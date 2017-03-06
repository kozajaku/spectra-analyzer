from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, emit
from spectra_downloader import SpectraDownloader
from .analyzer import Spectrum
import os
import time
import urllib
import click

DEFAULT_DIRECTORY = "/tmp/spectra"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sometotalbrutalsecret'
socketio = SocketIO(app)


# flask route specification

@app.route("/")
def index():
    """Index page shows welcome message and menu that guides client to spectra downloader and spectra analyzer tool."""
    return redirect(url_for('home'))


@app.route("/home")
def home():
    """Expanded index page"""
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


@socketio.on("connect", namespace="/downloader")
def connect():
    """
    This function is called whenever new socketio connection with the server from client is initiated to the /downloader
    namespace.
    """
    # print("Client connected: {}".format(request.sid))
    directory = request.cookies.get("last-directory")
    if directory is None:
        directory = DEFAULT_DIRECTORY
    else:
        directory = urllib.parse.unquote(directory)
    session["directory"] = directory


@socketio.on("disconnect", namespace="/downloader")
def disconnect():
    """This function is called whenever the socketio connection with the server is terminated by the client
    to the /downloader namespace."""
    # print("Client disconnected: {}".format(request.sid))
    pass


def format_size(size):
    """
    Returns string representation of file size in human readable format (using kB, MB, GB, TB units)
    :param size: Size of file in bytes.
    :return: String representation of size with SI units.
    """
    if size < 1000:
        return "{:d} B".format(size)
    for unit in ["k", "M", "G"]:
        size /= 1000.0
        if size < 1000.0:
            return "{:.2f} {}B".format(size, unit)
    return "{:.2f} TB".format(size)


def format_mtime(mtime):
    """
    Returns passed file modified time in human readable format.
    :param mtime: Time from epoch representing the time of file modification.
    :return: Human readable string representation of passed time.
    """
    return time.strftime("%H:%M:%S %d. %m. %Y", time.localtime(mtime))


def serialize_path(path, selected=None):
    """
    Returns json serializable object that can be sent to the client. This object
    represents one single directory that client decided to open. If a passed path
    does represent a file and not a directory, the listed directory of the file is
    returned and the specified file is marked as selected in the listing.
    :param path: Filesystem path that client wants to list.
    :param selected: Name of file in the directory specified by path argument that
    should be marked as a selected one.
    :return: Serializable dictionary.
    """
    path = os.path.abspath(path)  # normalize path
    if os.path.isdir(path):
        dirs = list()
        files = list()
        # append .. path
        dirs.append({"is_file": False, "name": "..", "path": os.path.dirname(path)})
        for name in os.listdir(path):
            new_path = os.path.join(path, name)
            if os.path.isdir(new_path):
                dirs.append({"is_file": False, "name": name, "path": new_path})
            elif os.path.isfile(new_path):
                size = format_size(os.path.getsize(new_path))
                mtime = format_mtime(os.path.getmtime(new_path))
                files.append({
                    "is_file": True,
                    "name": name,
                    "path": new_path,
                    "size": size,
                    "modified": mtime,
                    "selected": selected == name
                })
        return {"path": path, "invalid": False, "directory": dirs + files}
    elif os.path.isfile(path):
        return serialize_path(*os.path.split(path))
    else:
        return {"path": path, "invalid": True}


@socketio.on("connect", namespace="/analyzer")
def connect():
    """This function is called whenever new socketio connection with the server from client is initiated to the
    /analyzer namespace. Client must be instantly informed about the current directory."""
    path = session.get("directory")
    if path is None:
        path = request.cookies.get("last-directory")
        if path is None:
            path = "."
        else:
            path = urllib.parse.unquote(path)
    emit("directory_info", serialize_path(path), namespace="/analyzer")


@socketio.on("change_path", namespace="/analyzer")
def change_path(path):
    """This function is called whenever user wants to change directory either by changing
    path directly in the text box or by clicking to another directory in listing."""
    serialized = serialize_path(path)
    if not serialized["invalid"]:
        session["directory"] = path
    emit("directory_info", serialized, namespace="/analyzer")


@socketio.on("analyze_file", namespace="/analyzer")
def analyze_file(file_path):
    """This function is called by client when he selects a spectrum for analyzing."""
    if not os.path.isfile(file_path):
        res = {"invalid": True}
    else:
        spectrum = Spectrum.read_spectrum(file_path)
        if spectrum is None:
            res = {"invalid": True}
        else:
            session["spectrum"] = spectrum
            res = {
                "invalid": False,
                "spectrum_img": spectrum.plot_spectrum(),
                "freq0": spectrum.freq0,
                "wSize": spectrum.wSize,
                "scales": len(spectrum.scales),
                "cwt_img": spectrum.plot_cwt(),
                "transformation_img": spectrum.plot_reduced_spectrum(),
                "file_name": os.path.basename(file_path)}

    emit("file_analyzed", res, namespace="/analyzer")


@socketio.on("slider_changed", namespace="/analyzer")
def slider_changed(data):
    """This function is called whenever client moves with one of
    transformation parameter slider. It recounts transformation for
    the specified parameters and returns newly plotted image to the user."""
    freq0 = data['freq0']
    wSize = data['wSize']
    spectrum = session["spectrum"]
    spectrum.modify_parameters(freq0, wSize)
    emit("transformation_updated", spectrum.plot_reduced_spectrum(only_transformation=data['only-transformation']),
         namespace="/analyzer")


@socketio.on("only_transformation_changed", namespace="/analyzer")
def only_trans_changed(expected):
    """This function is called whenever client clicks on the checkbox - show only transformation.
    The transformation plot must be replotted and returned to the client."""
    spectrum = session["spectrum"]
    emit("transformation_updated", spectrum.plot_reduced_spectrum(only_transformation=expected), namespace="/analyzer")


@click.command()
@click.option("--debug", is_flag=True, help="Setup debug flags for Flask application.")
@click.option("--port", default=5000, help="TCP port of the web server.")
@click.option("--host", default="127.0.0.1", help="The hostname to listen on.")
def web(debug, port, host):
    """Setup click command for starting the spectra-analyzer from console."""
    socketio.run(app, debug=debug, port=port, host=host)


def main():
    web()
