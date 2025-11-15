# client_tcp.py
# Terminal client for the TCP chat server
# Usage: python3 client_tcp.py
# Commands:
#   /name NEWNAME      -> change username locally (and send join)
#   /file PATH         -> send a file at PATH
#   /quit              -> exit

import socket
import threading
import struct
import json
import os
from pathlib import Path

SERVER_HOST = '127.0.0.1'  # change to server IP if running across machines
SERVER_PORT = 9009         # must match server PORT
BUFFER = 4096
DOWNLOAD_DIR = Path('downloads')
DOWNLOAD_DIR.mkdir(exist_ok=True)

def recvall(sock, n):
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def send_framed(sock, header: dict, payload: bytes = None):
    header_bytes = json.dumps(header).encode('utf-8')
    sock.sendall(struct.pack('>I', len(header_bytes)))
    sock.sendall(header_bytes)
    if payload:
        sock.sendall(payload)

def receiver(sock):
    try:
        while True:
            raw = recvall(sock, 4)
            if raw is None:
                print("Disconnected from server.")
                break
            hdr_len = struct.unpack('>I', raw)[0]
            hdr_bytes = recvall(sock, hdr_len)
            if hdr_bytes is None:
                break
            header = json.loads(hdr_bytes.decode('utf-8'))
            typ = header.get('type')
            if typ == 'system':
                print(f"[SYSTEM] {header.get('text')}")
            elif typ == 'message':
                print(f"[{header.get('username')}] {header.get('text')}")
            elif typ == 'file':
                username = header.get('username')
                filename = header.get('filename')
                filesize = int(header.get('filesize', 0))
                # read file binary
                file_bytes = recvall(sock, filesize)
                if file_bytes is None:
                    print("File transfer interrupted")
                    break
                save_path = DOWNLOAD_DIR / filename
                with open(save_path, 'wb') as f:
                    f.write(file_bytes)
                print(f"[{username}] sent file saved as: {save_path} ({filesize} bytes)")
            else:
                print("Unknown incoming header:", header)
    except Exception as e:
        print("Receiver error:", e)
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    username = input("Enter your username: ").strip() or "Anonymous"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))
    # send join header
    send_framed(sock, {'type':'join', 'username': username})
    t = threading.Thread(target=receiver, args=(sock,), daemon=True)
    t.start()

    try:
        while True:
            cmd = input()
            if not cmd:
                continue
            if cmd.startswith('/file '):
                path = cmd[len('/file '):].strip()
                if not os.path.isfile(path):
                    print("File not found:", path)
                    continue
                size = os.path.getsize(path)
                fname = os.path.basename(path)
                with open(path, 'rb') as f:
                    data = f.read()
                header = {'type':'file', 'filename': fname, 'filesize': size}
                send_framed(sock, header, data)
                print(f"Sent file: {fname} ({size} bytes)")
            elif cmd.startswith('/name '):
                newname = cmd[len('/name '):].strip()
                if newname:
                    username = newname
                    print("Local username changed to", username)
                    # optionally inform server (resend join)
                    send_framed(sock, {'type':'join', 'username': username})
            elif cmd == '/quit':
                print("Quitting...")
                break
            else:
                # send as message
                header = {'type':'message', 'text': cmd}
                send_framed(sock, header)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            sock.close()
        except:
            pass

if __name__ == '__main__':
    main()
