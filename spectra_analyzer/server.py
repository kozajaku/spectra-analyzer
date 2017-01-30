from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from spectra_downloader import SpectraDownloader
import eventlet

DEFAULT_DIRECTORY = "/tmp/spectra"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # todo change
socketio = SocketIO(app)


# flask route specification

@app.route("/")
def index():
    """Index page shows welcome message and menu that guides client to spectra downloader and spectra analyzer tool."""
    return render_template('index.html', async_mode=socketio.async_mode)


@app.route("/downloader")
def downloader():
    """Renders template for spectra downloader application."""
    return render_template("downloader.html", async_mode=socketio.async_mode)


@app.route("/analyzer")
def analyzer():
    """Renders template for spectra analyzer application."""
    return render_template("analyzer.html", async_mode=socketio.async_mode)


@app.errorhandler(404)
def page_not_found(error):
    return redirect(url_for('index'))


@socketio.on("votable_text", namespace="/downloader")
def votable_text(message):
    """
    This function is called when socketio event comes with tag votable_text.
    This event is triggered by client when he has votable data and he sends
    them to the server for parsing.
    :param message: Message containing votable text.
    """
    process_vot(votable=message)


@socketio.on("votable_url", namespace="/downloader")
def votable_url(url):
    """
    This function is called when socketio event comes when client obtains
    url to SSAP service endpoint.
    :param url: Url address to SSAP service endpoint including query parameters.
    """
    process_vot(url=url)


def process_vot(url=None, votable=None):
    """
    Process votable referenced either with URL or direct String text form.
    Client is informed about parsing and downloading result.
    Note that either url or votable parameters must be provided. In case that
    both parameters are provided, url parameter takes precedence.
    :param url: Resource URL where SSAP VOTABLE can be downloaded from.
    :param votable: VOTABLE saved as a String.
    """
    if url is None and votable is None:
        raise ValueError("Either link or votable argument must be provided.")
    try:
        if url is not None:
            spectra_downloader = SpectraDownloader.from_link(url)
        else:
            spectra_downloader = SpectraDownloader.from_string(votable)
        parsed = spectra_downloader.parsed_ssap
        response = {
            "success": True,
            "link_known": url is not None,
            "link": "unknown" if url is None else url,
            "directory": session["directory"],
            "query_status": parsed.query_status,
            "record_count": len(parsed.rows),
            "datalink_available": parsed.datalink_available
        }
        # return spectra list (index, spectrum_name)
        spectra = [(idx, parsed.get_refname(spectrum)) for idx, spectrum in enumerate(parsed.rows)]
        response["spectra"] = spectra
        # add DataLink specification if any
        if parsed.datalink_available:
            datalink = list()
            for param in parsed.datalink_input_params:
                if param.id_param:
                    continue
                if len(param.options) == 0:
                    tmp = {"name": param.name, "select": False}
                else:
                    tmp = {"name": param.name, "select": True}
                    options = list()
                    for option in param.options:
                        options.append({"name": option.name, "value": option.value})
                    tmp["options"] = options
                datalink.append(tmp)
            response["datalink"] = datalink

        # save downloader into the session
        session["downloader"] = spectra_downloader
    except Exception as ex:
        response = {
            "success": False,
            "exception": str(ex),
            "link_known": url is not None,
            "link": "unknown" if url is None else url
        }
    # emit response to the client
    emit("votable_parsed", response, namespace="/downloader")  # context is still available


@socketio.on("download_spectra", namespace="/downloader")
def download_spectra(message):
    """
    This function is invoked when client collects all necessary information about
    spectra download from user and when the downloading itself should be initiated.
    :param message: Message from the client. It contains selected spectra IDs to be downloaded,
    target directory and in case of DataLink protocol availability - if the protocol
    should be used and what options should be applied.
    """
    # obtain downloader from the session
    spectra_downloader = session.get("downloader")
    if spectra_downloader is None:
        return redirect(url_for('downloader'))
    # fetch information from message
    spectra_ids = message.get('spectra')
    directory = message.get('directory')
    use_datalink = message.get('use-datalink')
    if spectra_ids is None or directory is None or use_datalink is None:
        # invalid message
        return redirect(url_for('downloader'))
    # save directory into session
    session["directory"] = directory
    spectra = list(map(lambda i: spectra_downloader.parsed_ssap.rows[int(i)], spectra_ids))
    if use_datalink:
        datalink = message.get('datalink')
        if datalink is None:
            return redirect(url_for('downloader'))
        socketio.start_background_task(spectra_downloader.download_datalink, spectra, datalink, directory,
                                       progress_callback=download_progress(request.sid),
                                       done_callback=download_finished(request.sid), async=False)
    else:
        socketio.start_background_task(spectra_downloader.download_direct, spectra, directory,
                                       progress_callback=download_progress(request.sid),
                                       done_callback=download_finished(request.sid), async=False)


def download_progress(sid):
    """
    This function serves as a factory for progress callbacks. These callbacks
    are created when clients initiates spectra downloading and they want to be
    informed about progress.
    :param sid: Client's socketio connection identifier.
    :return: Callback method taking argument by the spectra-downloader specification.
    """

    def callback(result):
        message = dict()
        message["file_name"] = result.name
        message["url"] = result.url
        message["success"] = result.success
        if not result.success:
            message["exception"] = str(result.exception)
        socketio.emit("spectrum_downloaded", message, namespace="/downloader", room=sid)
        socketio.sleep()  # this is necessary to force flush message

    return callback


def download_finished(sid):
    """
    This function serves as a factory for done callbacks. These callbacks are
    used to signalize client that the spectra downloading process has finished.
    :param sid: Client's socketio connection identifier.
    :return: Callback method taking one boolean argument signalizing success.
    """

    def callback(success):
        socketio.emit("spectra_downloaded", success, namespace="/downloader", room=sid)

    return callback


@socketio.on('connect', namespace='/downloader')
def connect():
    """
    This method is called whenever new socketio connection with server from client is initiated.
    """
    print("Client connected: {}".format(request.sid))
    directory = session.get("directory")
    if directory is None:
        session["directory"] = DEFAULT_DIRECTORY


@socketio.on('disconnect', namespace='/downloader')
def disconnect():
    """This method is called whenever the socketio connection with the server is terminated by the client."""
    print("Client disconnected: {}".format(request.sid))


if __name__ == "__main__":
    socketio.run(app, debug=False)
