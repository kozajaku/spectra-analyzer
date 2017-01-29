from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, \
    close_room, rooms, disconnect
from spectra_downloader import SpectraDownloader

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
    This method is called when socketio event comes with tag votable_text.
    This event is triggered by client when he has votable data and he sends
    them to the server for parsing.
    :param message: Message containing votable text.
    """
    process_vot(votable=message)


@socketio.on("votable_url", namespace="/downloader")
def votable_url(url):
    """
    This method is called when socketio event comes when client obtains
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
            "query_status": parsed.query_status,
            "record_count": len(parsed.rows),
            "datalink_available": parsed.datalink_available
        }
        # return spectra list (index, spectrum_name)
        spectra = [(idx, parsed.get_refname(spectrum)) for idx, spectrum in enumerate(parsed.rows)]
        response["spectra"] = spectra
        # add DataLink specification if any
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


def background_thread(sid):
    """Example of how to send server generated events to clients."""
    print(sid)

    def every_client():
        count = 0
        while True:
            socketio.sleep(10)
            count += 1
            print("emit")
            socketio.emit('my_response',
                          {'data': 'Server generated event', 'count': count}, namespace="/test",
                          room=sid)

    return every_client


@socketio.on('my_event', namespace='/test')
def test_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']})


@socketio.on('my_broadcast_event', namespace='/test')
def test_broadcast_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         broadcast=True)


@socketio.on('join', namespace='/test')
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('leave', namespace='/test')
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count']})


@socketio.on('close_room', namespace='/test')
def close(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
                         'count': session['receive_count']},
         room=message['room'])
    close_room(message['room'])


@socketio.on('my_room_event', namespace='/test')
def send_room_message(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count']},
         room=message['room'])


@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()


@socketio.on('my_ping', namespace='/test')
def ping_pong():
    emit('my_pong')


@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    if thread is None:
        thread = socketio.start_background_task(target=background_thread(request.sid))
    emit('my_response', {'data': 'Connected', 'count': 0})


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == "__main__":
    socketio.run(app, debug=True)
