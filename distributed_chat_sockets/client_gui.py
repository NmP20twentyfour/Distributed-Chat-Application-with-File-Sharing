# client_gui.py (complete improved GUI with clickable received file links)
# Usage: python3 client_gui.py
#
# NOTE: Make sure SERVER_HOST and SERVER_PORT match your server_tcp.py settings.

import socket
import threading
import struct
import json
import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# === CONFIG ===
SERVER_HOST = '127.0.0.1'   # change to server IP when running on different machine
SERVER_PORT = 9009
DOWNLOAD_DIR = Path('downloads_gui')
DOWNLOAD_DIR.mkdir(exist_ok=True)
CHUNK_SIZE = 64 * 1024  # 64 KB chunks for sending files (so progress can be shown)
# ==============

def recvall(sock, n):
    """Receive exactly n bytes or return None if connection closed."""
    data = bytearray()
    while len(data) < n:
        try:
            packet = sock.recv(n - len(data))
        except Exception:
            return None
        if not packet:
            return None
        data.extend(packet)
    return bytes(data)

def send_header(sock, header):
    """Send framed JSON header: [4-byte len][header_json]."""
    hb = json.dumps(header).encode('utf-8')
    sock.sendall(struct.pack('>I', len(hb)))
    sock.sendall(hb)

def open_file(path: Path):
    """Open a file with the default OS application (cross-platform)."""
    try:
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', str(path)))
        elif os.name == 'nt':
            os.startfile(str(path))
        elif os.name == 'posix':
            subprocess.call(('xdg-open', str(path)))
    except Exception as e:
        messagebox.showerror("Cannot open file", str(e))

class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Chat — GUI")
        self.sock = None
        self.receiver_thread = None
        self.username = tk.StringVar(value="GUIUser")
        self.status_var = tk.StringVar(value="Disconnected")
        self.users = set()
        self._file_link_counter = 0

        self._build_ui()
        self._style_ui()

    def _build_ui(self):
        # top frame
        top = ttk.Frame(self.root, padding=(8,8,8,4))
        top.pack(fill='x')

        ttk.Label(top, text="Username:").pack(side='left')
        self.name_entry = ttk.Entry(top, textvariable=self.username, width=20)
        self.name_entry.pack(side='left', padx=(4,8))

        self.connect_btn = ttk.Button(top, text="Connect", command=self.connect)
        self.connect_btn.pack(side='left')

        self.disconnect_btn = ttk.Button(top, text="Disconnect", command=self.disconnect, state='disabled')
        self.disconnect_btn.pack(side='left', padx=(8,0))

        ttk.Label(top, textvariable=self.status_var, foreground='#666').pack(side='right')

        # main content: split left (chat) and right (user list + file)
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill='both', expand=True)

        # Chat area
        chat_frame = ttk.Frame(main)
        chat_frame.pack(side='left', fill='both', expand=True)

        self.chat_text = tk.Text(chat_frame, wrap='word', state='disabled', height=20, padx=8, pady=8, bd=0)
        self.chat_text.pack(fill='both', expand=True, side='left')
        self.chat_text.tag_configure('system', foreground='#666', font=('Helvetica', 9, 'italic'))
        self.chat_text.tag_configure('me', foreground='#0b5394', font=('Helvetica', 10, 'bold'))
        self.chat_text.tag_configure('other', foreground='#1a1a1a', font=('Helvetica', 10))
        self.chat_text.tag_configure('time', foreground='#888', font=('Helvetica', 8))

        chat_scroll = ttk.Scrollbar(chat_frame, orient='vertical', command=self.chat_text.yview)
        chat_scroll.pack(side='right', fill='y')
        self.chat_text['yscrollcommand'] = chat_scroll.set

        # Right pane: users + file controls
        right_frame = ttk.Frame(main, width=260)
        right_frame.pack(side='right', fill='y', padx=(10,0))

        ttk.Label(right_frame, text="Participants", font=('Helvetica', 10, 'bold')).pack(anchor='w')
        self.user_listbox = tk.Listbox(right_frame, height=10, activestyle='none', bd=0, highlightthickness=0)
        self.user_listbox.pack(fill='x', pady=(4,8))

        ttk.Separator(right_frame, orient='horizontal').pack(fill='x', pady=6)

        ttk.Label(right_frame, text="File Transfer", font=('Helvetica', 10, 'bold')).pack(anchor='w')
        self.file_label = ttk.Label(right_frame, text="No file selected", foreground='#555')
        self.file_label.pack(anchor='w', pady=(4,4))
        self.attach_btn = ttk.Button(right_frame, text="Attach & Send File", command=self.choose_and_send_file, state='disabled')
        self.attach_btn.pack(fill='x')

        self.progress = ttk.Progressbar(right_frame, orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', pady=(8,0))

        # input frame
        input_frame = ttk.Frame(self.root, padding=(8,6))
        input_frame.pack(fill='x')

        self.msg_entry = ttk.Entry(input_frame)
        self.msg_entry.pack(side='left', fill='x', expand=True, padx=(0,8))
        self.msg_entry.bind('<Return>', lambda e: self.send_msg())

        self.send_btn = ttk.Button(input_frame, text="Send", command=self.send_msg, state='disabled')
        self.send_btn.pack(side='left')

    def _style_ui(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except:
            pass
        style.configure('TButton', padding=6)
        style.configure('TEntry', padding=6)
        style.configure('TLabel', padding=2)

    def append(self, text, tag=None, include_time=True):
        timestamp = ''
        if include_time:
            timestamp = datetime.now().strftime('%H:%M')
        def do():
            self.chat_text.config(state='normal')
            if tag == 'system':
                self.chat_text.insert('end', f"{text}\n", 'system')
            else:
                if include_time:
                    self.chat_text.insert('end', f"[{timestamp}] ", 'time')
                if tag == 'me':
                    self.chat_text.insert('end', f"You: {text}\n", 'me')
                elif tag == 'other':
                    self.chat_text.insert('end', f"{text}\n", 'other')
                else:
                    self.chat_text.insert('end', f"{text}\n")
            self.chat_text.see('end')
            self.chat_text.config(state='disabled')
        self.root.after(0, do)

    def update_user_list(self):
        def do():
            self.user_listbox.delete(0, 'end')
            for u in sorted(self.users):
                self.user_listbox.insert('end', u)
        self.root.after(0, do)

    def connect(self):
        if self.sock:
            messagebox.showinfo("Info", "Already connected.")
            return
        host = SERVER_HOST
        port = SERVER_PORT
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            self.sock = sock
            self.status_var.set(f"Connected to {host}:{port}")
            self.connect_btn.config(state='disabled')
            self.disconnect_btn.config(state='normal')
            self.send_btn.config(state='normal')
            self.attach_btn.config(state='normal')
            self.username_str = self.username.get().strip() or "GUIUser"
            # send join header
            send_header(self.sock, {'type':'join','username': self.username_str})
            self.append("Connected.", tag='system', include_time=False)
            # start receiver thread
            self.receiver_thread = threading.Thread(target=self.receiver, daemon=True)
            self.receiver_thread.start()
        except Exception as e:
            messagebox.showerror("Connection error", str(e))

    def disconnect(self):
        if not self.sock:
            return
        try:
            self.sock.close()
        except:
            pass
        self.sock = None
        self.status_var.set("Disconnected")
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.send_btn.config(state='disabled')
        self.attach_btn.config(state='disabled')
        self.append("Disconnected.", tag='system')

    def receiver(self):
        try:
            while self.sock:
                raw = recvall(self.sock, 4)
                if raw is None:
                    break
                hdr_len = struct.unpack('>I', raw)[0]
                hdr_bytes = recvall(self.sock, hdr_len)
                if hdr_bytes is None:
                    break
                header = json.loads(hdr_bytes.decode('utf-8'))
                typ = header.get('type')
                if typ == 'system':
                    text = header.get('text', '')
                    if 'joined' in text:
                        who = text.split(' joined')[0]
                        self.users.add(who)
                        self.update_user_list()
                    if 'left' in text:
                        who = text.split(' left')[0]
                        if who in self.users:
                            self.users.remove(who)
                            self.update_user_list()
                    self.append(text, tag='system')

                elif typ == 'message':
                    user = header.get('username', 'Anon')
                    text = header.get('text', '')
                    self.append(f"{user}: {text}", tag='other')
                    self.users.add(user)
                    self.update_user_list()

                elif typ == 'file':
                    username = header.get('username', 'someone')
                    filename = header.get('filename')
                    filesize = int(header.get('filesize', 0))

                    # read file bytes
                    file_bytes = recvall(self.sock, filesize)
                    if file_bytes is None:
                        self.append("File transfer interrupted", tag='system')
                        continue

                    save_path = DOWNLOAD_DIR / filename
                    # avoid overwrite
                    i = 1
                    base = save_path.stem
                    suf = save_path.suffix
                    while save_path.exists():
                        save_path = DOWNLOAD_DIR / f"{base}_{i}{suf}"
                        i += 1

                    with open(save_path, 'wb') as f:
                        f.write(file_bytes)

                    # Add to chat as a clickable link
                    self.users.add(username)
                    self.update_user_list()

                    tag_name = f"filelink_{self._file_link_counter}"
                    self._file_link_counter += 1
                    display_text = f"{username} sent file: {save_path.name} (click to open)\n"

                    def make_insert(path, tag):
                        def _do():
                            self.chat_text.config(state='normal')
                            # insert timestamp
                            self.chat_text.insert('end', datetime.now().strftime('[%H:%M] '), 'time')
                            start_index = self.chat_text.index('end-1c')
                            self.chat_text.insert('end', display_text, tag)
                            self.chat_text.see('end')
                            self.chat_text.config(state='disabled')
                            # configure tag appearance and bind click
                            self.chat_text.tag_configure(tag, foreground='#0066cc', underline=True)
                            self.chat_text.tag_bind(tag, '<Button-1>', lambda e, p=path: open_file(p))
                        return _do

                    self.root.after(0, make_insert(save_path, tag_name))

                else:
                    self.append(f"Unknown: {header}", tag='system')
        except Exception as e:
            self.append("Receiver error: " + str(e), tag='system')
        finally:
            try:
                if self.sock:
                    self.sock.close()
            except:
                pass
            self.sock = None
            self.root.after(0, lambda: self.disconnect())

    def send_msg(self):
        if not self.sock:
            messagebox.showwarning("Warning", "Not connected")
            return
        txt = self.msg_entry.get().strip()
        if not txt:
            return
        header = {'type':'message', 'text': txt}
        try:
            send_header(self.sock, header)
            # show locally
            self.append(txt, tag='me')
            self.msg_entry.delete(0, 'end')
        except Exception as e:
            messagebox.showerror("Send error", str(e))
            self.disconnect()

    def choose_and_send_file(self):
        if not self.sock:
            messagebox.showwarning("Warning", "Not connected")
            return
        path = filedialog.askopenfilename()
        if not path:
            return
        self.file_label.config(text=os.path.basename(path))
        t = threading.Thread(target=self._send_file_thread, args=(path,), daemon=True)
        t.start()

    def _send_file_thread(self, path):
        try:
            total = os.path.getsize(path)
            fname = os.path.basename(path)
            header = {'type':'file', 'filename': fname, 'filesize': total}
            # send header first
            send_header(self.sock, header)
            # send file in chunks so we can update progressbar
            self.root.after(0, lambda: self.progress.configure(maximum=total, value=0))
            sent = 0
            with open(path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.sock.sendall(chunk)
                    sent += len(chunk)
                    # update progress
                    self.root.after(0, lambda s=sent: self.progress.configure(value=s))
            # completed
            self.root.after(0, lambda: self.append(f"You sent file: {fname} ({total} bytes)", tag='me'))
            self.root.after(0, lambda: self.progress.configure(value=0))
            self.root.after(0, lambda: self.file_label.config(text="No file selected"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("File send error", str(e)))
            self.root.after(0, lambda: self.progress.configure(value=0))

if __name__ == '__main__':
    import struct, json
    root = tk.Tk()
    app = ChatClientGUI(root)
    root.geometry('900x560')
    root.minsize(900, 560)
    root.mainloop()
