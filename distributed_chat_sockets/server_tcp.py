# server_tcp.py
# TCP multi-client chat server with file broadcasting
# Usage: python3 server_tcp.py
# Requirements: Python 3.8+

import socket
import threading
import struct
import json
import os
from pathlib import Path
from typing import Dict, Tuple

HOST = '0.0.0.0'   # change here if you want server bind to specific interface
PORT = 9009        # change here to use different port
UPLOAD_DIR = Path('uploads')
UPLOAD_DIR.mkdir(exist_ok=True)

# Global list of connected clients: list of tuples (socket, address, username)
clients = []
clients_lock = threading.Lock()

def recvall(sock: socket.socket, n: int) -> bytes:
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def send_framed(sock: socket.socket, header: Dict, payload: bytes = None):
    """
    Send: [4-byte header_len][header_json][optional payload bytes]
    """
    header_bytes = json.dumps(header).encode('utf-8')
    sock.sendall(struct.pack('>I', len(header_bytes)))
    sock.sendall(header_bytes)
    if payload:
        sock.sendall(payload)

def broadcast_except(sender_sock: socket.socket, header: Dict, payload: bytes = None):
    with clients_lock:
        to_remove = []
        for c_sock, addr, username in clients:
            if c_sock is sender_sock:
                continue
            try:
                send_framed(c_sock, header, payload)
            except Exception as e:
                print(f"Error sending to {addr}: {e}")
                to_remove.append((c_sock, addr, username))
        for r in to_remove:
            clients.remove(r)

def handle_client(client_sock: socket.socket, addr: Tuple[str,int]):
    username = None
    try:
        while True:
            # read 4 bytes => header length
            raw = recvall(client_sock, 4)
            if not raw:
                print(f"Client {addr} disconnected")
                break
            hdr_len = struct.unpack('>I', raw)[0]
            hdr_bytes = recvall(client_sock, hdr_len)
            if hdr_bytes is None:
                break
            header = json.loads(hdr_bytes.decode('utf-8'))
            typ = header.get('type')
            if typ == 'join':
                username = header.get('username', f'{addr[0]}:{addr[1]}')
                with clients_lock:
                    clients.append((client_sock, addr, username))
                print(f"{username} joined from {addr}")
                sys_hdr = {'type':'system', 'text': f'{username} joined'}
                broadcast_except(client_sock, sys_hdr, None)
            elif typ == 'message':
                text = header.get('text', '')
                print(f"[{username}] {text}")
                out_hdr = {'type':'message', 'username': username, 'text': text}
                broadcast_except(client_sock, out_hdr, None)
            elif typ == 'file':
                filename = header.get('filename', 'file.bin')
                filesize = int(header.get('filesize', 0))
                # read exactly filesize bytes
                file_bytes = recvall(client_sock, filesize)
                if file_bytes is None:
                    break
                # save file with collision avoidance
                safe = os.path.basename(filename)
                save_path = UPLOAD_DIR / safe
                i = 1
                stem = save_path.stem
                suf = save_path.suffix
                while save_path.exists():
                    save_path = UPLOAD_DIR / f"{stem}_{i}{suf}"
                    i += 1
                with open(save_path, 'wb') as f:
                    f.write(file_bytes)
                print(f"Received file from {username}: {save_path} ({filesize} bytes)")
                # broadcast file to others (header will contain original filename + saved name + filesize)
                out_hdr = {
                    'type':'file',
                    'username': username,
                    'filename': save_path.name,
                    'orig_filename': filename,
                    'filesize': filesize
                }
                broadcast_except(client_sock, out_hdr, file_bytes)
            else:
                # unknown type - ignore or send error
                err = {'type':'system', 'text':'Unknown message type'}
                send_framed(client_sock, err)
    except Exception as e:
        print(f"Exception handling client {addr}: {e}")
    finally:
        # remove from clients
        with clients_lock:
            clients[:] = [c for c in clients if c[0] is not client_sock]
        if username:
            print(f"{username} disconnected")
            broadcast_except(client_sock, {'type':'system','text':f'{username} left'}, None)
        try:
            client_sock.close()
        except:
            pass

def main():
    print(f"Starting TCP Chat Server on {HOST}:{PORT}")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(100)
    try:
        while True:
            client_sock, addr = server.accept()
            print(f"New connection from {addr}")
            t = threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        server.close()

if __name__ == '__main__':
    main()
