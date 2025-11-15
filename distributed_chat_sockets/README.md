# 📡 Distributed Chat Application with File Sharing

**Course:** CS401 (25) – Introduction to Distributed and Parallel Computing
**Institute:** IIIT Vadodara

**Team Members:**

* **Neelmadhav Padhi – 202251074**
* **Mudavath Ram – 202251073**
* **Kampa Karthik – 202251061**

---

## 📘 Project Overview

This project implements a **distributed multi-client chat system** with **real-time messaging**, **file sharing**, and **dual-interface support** (Desktop GUI + Web Client).
A `TCP-based server` handles all communication, ensuring reliable delivery and concurrent connections using threading.

The system includes a **web bridge** that exposes the chat/file-sharing functionality to a browser using Flask, WebSockets, and JavaScript.

---

## 🏗️ Key Features

### 🔥 **1. Multi-Client Real-Time Chat (TCP)**

* Unlimited client connections (bounded by hardware).
* Broadcast messaging to all active users.
* Clean command-line & GUI interface.

### 📤 **2. File Transfer System**

* Send files of any type (PDF, images, videos, etc.).
* Chunk-based transmission ensures no corruption.
* Files stored in `/uploads/` and `/downloads/`.

### 🖥️ **3. Graphical Client (Python Tkinter)**

* Message pane, input box, file-selection dialog.
* Supports both chat and file transfer.

### 🌐 **4. Web Client (HTML + JS + Flask Bridge)**

* Accessible via browser.
* Uses WebSockets via the `web_bridge/` module.
* Modern UI using CSS (`static/style.css`).

### 🧵 **5. Concurrent TCP Server**

* Handles multiple clients via threading.
* Separate threads for receiving and sending.

---

## 📂 Project Structure

The structure below matches your screenshot:

```
DISTRIBUTED_CHAT_SOCKETS/
│
├── downloads/                # Downloaded files (TCP client)
├── downloads_gui/            # Downloaded files (GUI client)
│
├── uploads/                  # Uploaded files (TCP/GUI/web)
│   ├── PhysRevApplied.pdf
│   └── Screen Recording.mp4
│
├── venv/                     # Virtual environment (ignored in submission)
│
├── web_bridge/               # Web-based chat/file interface
│   ├── static/
│   │   ├── client.js         # Browser-side JS
│   │   └── style.css         # Styling
│   ├── templates/
│   │   └── index.html        # Web chat UI
│   ├── uploads/              # Web-uploaded files
│   └── bridge.py             # Flask + WebSocket bridge server
│
├── client_gui.py             # Tkinter GUI client
├── client_tcp.py             # Terminal-based TCP client
├── server_tcp.py             # TCP chat server
│
├── requirements.txt          # Dependencies
├── protocols.md              # Notes on chat + file transfer protocol
└── README.md                 # (You are here)
```

---

## 🚀 How to Run the Project

### 🔧 **1. Install Dependencies**

```bash
pip install -r requirements.txt
```

---

## 🖥️ **Option A — Run the TCP Chat System**

### **Start the Server**

```bash
python server_tcp.py
```

### **Start a TCP Client**

```bash
python client_tcp.py
```

### **Start GUI Client**

```bash
python client_gui.py
```

---

## 🌐 **Option B — Run the Web Client**

### **Start Web Bridge**

```bash
cd web_bridge
python bridge.py
```

Open in browser:

```
http://127.0.0.1:5000
```

You can:

* Send/receive chat messages
* Upload & download files
* View connected users

---

## 📡 Communication Protocol

Documented in **`protocols.md`**, including:

* Message format
* File metadata structure
* Chunked file transfer logic
* Error handling
* Server-side routing rules

Example (from server):

```python
conn, addr = server.accept()
threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
```

---

## 📦 Results & Observations

* Real-time chat with **0 message loss** using TCP.
* File transfers of **large PDFs, videos, images** tested successfully.
* GUI client and Web client both operate seamlessly with the same server.
* Supports simultaneous:

  * Multiple TCP clients
  * Multiple GUI clients
  * Multiple Web clients

---

## 📈 Future Improvements

* End-to-end encryption (TLS sockets)
* User login & authentication
* Chat rooms / private messaging
* Persistent chat history using database
* Full React/Flutter web client
* Async server using `asyncio` for higher scalability

---

## 🏁 Conclusion

This project demonstrates practical distributed systems concepts including:

✔ concurrent server design
✔ socket programming
✔ protocol design
✔ web integration
✔ parallel client handling

