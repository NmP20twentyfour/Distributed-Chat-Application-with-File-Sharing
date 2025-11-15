import os, socket, struct, json, base64, threading, traceback
from pathlib import Path
from flask import Flask, render_template, request as flask_request, send_from_directory
from flask_socketio import SocketIO

# Configuration
TCP_SERVER_HOST = '127.0.0.1'
TCP_SERVER_PORT = 9009
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace-me'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

clients = {}
clients_lock = threading.Lock()

def send_framed(sock, header, payload=None):
    header_bytes = json.dumps(header).encode('utf-8')
    sock.sendall(struct.pack('>I', len(header_bytes)))
    sock.sendall(header_bytes)
    if payload:
        sock.sendall(payload)

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
        except:
            return None
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def tcp_reader(sid):
    with clients_lock:
        info = clients.get(sid)
    if not info:
        return
    sock = info['sock']
    print(f"[bridge] tcp_reader started for {sid}")
    try:
        while info.get('alive'):
            raw = recvall(sock, 4)
            if not raw: break
            hdr_len = struct.unpack('>I', raw)[0]
            header = json.loads(recvall(sock, hdr_len).decode())
            typ = header.get('type')
            if typ == 'file':
                fname = header.get('filename', 'file.bin')
                fsize = int(header.get('filesize', 0))
                data = recvall(sock, fsize)
                if not data: continue
                save_path = UPLOAD_DIR / fname
                with open(save_path, 'wb') as f: f.write(data)
                url = f"/uploads/{fname}"
                socketio.emit('file', {
                    'username': header.get('username', 'Server'),
                    'filename': fname,
                    'filesize': fsize,
                    'url': url
                }, room=sid)
                print(f"[bridge] File saved: {save_path}")
            else:
                socketio.emit('message', header, room=sid)
    except Exception as e:
        traceback.print_exc()
    finally:
        print(f"[bridge] tcp_reader ended for {sid}")
        sock.close()
        with clients_lock:
            clients.pop(sid, None)
        socketio.emit('system', {'text': 'Disconnected from TCP server'}, room=sid)
        socketio.disconnect(sid)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)

@socketio.on('connect')
def on_connect():
    sid = flask_request.sid
    print(f"[bridge] Connected: {sid}")
    socketio.emit('system', {'text': 'Connected to bridge'}, room=sid)

@socketio.on('join')
def handle_join(data):
    sid = flask_request.sid
    username = data.get('username', 'WebUser')
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((TCP_SERVER_HOST, TCP_SERVER_PORT))
        send_framed(sock, {'type': 'join', 'username': username})
        with clients_lock:
            clients[sid] = {'sock': sock, 'alive': True}
        socketio.start_background_task(tcp_reader, sid)
        socketio.emit('system', {'text': f'Joined as {username}'}, room=sid)
        print(f"[bridge] {sid} joined as {username}")
    except Exception as e:
        socketio.emit('system', {'text': f'Error: {e}'}, room=sid)

@socketio.on('message')
def handle_message(data):
    sid = flask_request.sid
    text = data.get('text', '')
    with clients_lock:
        info = clients.get(sid)
    if not info:
        socketio.emit('system', {'text': 'Not connected'}, room=sid)
        return
    try:
        send_framed(info['sock'], {'type': 'message', 'text': text, 'username': data.get('username')})
    except Exception as e:
        socketio.emit('system', {'text': f'Error sending message: {e}'}, room=sid)

@socketio.on('file-start')
def handle_file_start(data):
    sid = flask_request.sid
    filename = data.get('filename')
    filesize = int(data.get('filesize', 0))
    username = data.get('username', 'WebUser')
    with clients_lock:
        info = clients.get(sid)
    if not info: return
    send_framed(info['sock'], {'type': 'file', 'filename': filename, 'filesize': filesize, 'username': username})
    info['file'] = {'remaining': filesize}
    socketio.emit('system', {'text': f"Uploading {filename}..."}, room=sid)

@socketio.on('file-chunk')
def handle_file_chunk(data):
    sid = flask_request.sid
    chunk = base64.b64decode(data.get('chunk_b64'))
    with clients_lock:
        info = clients.get(sid)
    if not info: return
    try:
        info['sock'].sendall(chunk)
    except:
        pass

@socketio.on('file-end')
def handle_file_end(data=None):
    sid = flask_request.sid
    socketio.emit('system', {'text': 'File upload complete!'}, room=sid)
    print(f"[bridge] file-end from {sid}")

@socketio.on('disconnect')
def handle_disconnect():
    sid = flask_request.sid
    print(f"[bridge] Disconnect {sid}")
    with clients_lock:
        info = clients.pop(sid, None)
    if info:
        info['alive'] = False
        try:
            info['sock'].close()
        except:
            pass

if __name__ == '__main__':
    print(f"Running Web Bridge on http://{FLASK_HOST}:{FLASK_PORT}")
    socketio.run(app, host=FLASK_HOST, port=FLASK_PORT)
