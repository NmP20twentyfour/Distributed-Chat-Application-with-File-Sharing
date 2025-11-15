// client.js — updated theme init + UI logic
// Make sure this file replaces your previous client.js

// --- Theme initialization (runs immediately) ---
(function initTheme() {
  try {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
      document.documentElement.classList.add('dark'); // optional: root-level class
      document.body.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
      document.body.classList.remove('dark');
    }
  } catch (e) {
    // localStorage might be disabled — ignore
    console.warn('theme init error', e);
  }
})();

// Helper to update toggle icon
function updateThemeToggleIcon() {
  const t = document.getElementById('themeToggle');
  if (!t) return;
  const isDark = document.body.classList.contains('dark');
  t.textContent = isDark ? '☀️' : '🌙';
}

// Wire toggle (runs early)
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    updateThemeToggleIcon();
    themeToggle.addEventListener('click', () => {
      const darkNow = document.body.classList.toggle('dark');
      try { localStorage.setItem('theme', darkNow ? 'dark' : 'light'); } catch (e) {}
      updateThemeToggleIcon();
    });
  }
});

// --- Socket + UI logic (rest of file) ---
const socket = io();

// DOM
const connectBtn = document.getElementById('connect');
const usernameInput = document.getElementById('username');
const statusEl = document.getElementById('status');
const messagesEl = document.getElementById('messages');
const msgInput = document.getElementById('msgInput');
const sendBtn = document.getElementById('send');
const chooseBtn = document.getElementById('chooseBtn');
const fileInput = document.getElementById('fileInput');
const fileNameLabel = document.getElementById('fileName');
const sendFileBtn = document.getElementById('sendFile');
const uploadProgress = document.getElementById('uploadProgress');
const autoDownload = document.getElementById('autoDownload');

let myName = null;

function escapeHtml(s){ return String(s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function appendMessage({ username, text, me=false, file=false, html=null }){
  const li = document.createElement('li');
  li.className = 'msg' + (me ? ' me' : '') + (file ? ' file' : '');
  let meta = `<div class="meta">${escapeHtml(username || 'System')} • ${new Date().toLocaleTimeString()}</div>`;
  let body = html ? html : `<div class="text">${escapeHtml(text||'')}</div>`;
  li.innerHTML = meta + body;
  messagesEl.appendChild(li);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// socket handlers
socket.on('system', d => appendMessage({ username:'System', text:d.text }));
socket.on('message', d => appendMessage({ username:d.username||'User', text:d.text }));
socket.on('file', d => {
  const user = d.username || 'User';
  const filename = d.filename || 'file';
  const url = d.url ? (d.url.startsWith('/') ? (location.origin + d.url) : d.url) : null;

  const ext = filename.split('.').pop().toLowerCase();
  if(url && ['png','jpg','jpeg','gif','webp','bmp','svg'].includes(ext)){
    const html = `<div class="file-preview"><img src="${url}" alt="${escapeHtml(filename)}"/></div>`;
    appendMessage({ username:user, html:html, file:true });
  } else if(url && ['mp4','webm','ogg','m4v','mov'].includes(ext)){
    const html = `<div class="file-preview"><video controls src="${url}" style="max-width:100%;border-radius:8px;"></video></div>`;
    appendMessage({ username:user, html:html, file:true });
  } else if(url && ext === 'pdf'){
    const html = `<div class="file-preview"><iframe src="${url}" style="width:100%;height:360px;border:0;border-radius:8px;"></iframe></div>`;
    appendMessage({ username:user, html:html, file:true });
  } else {
    const link = url ? `<a href="${url}" target="_blank" rel="noopener">${escapeHtml(filename)}</a>` : escapeHtml(filename);
    appendMessage({ username:user, html:`<div class="text">📎 ${link} (${d.filesize||0} bytes)</div>`, file:true });
  }

  if(autoDownload.checked && url){
    window.open(url, '_blank');
  }
});

socket.on('connect', () => statusEl.textContent = 'Connected');
socket.on('disconnect', () => statusEl.textContent = 'Disconnected');

connectBtn.addEventListener('click', ()=>{
  myName = usernameInput.value.trim() || ('Web' + Math.floor(Math.random()*1000));
  socket.emit('join', { username: myName });
  statusEl.textContent = 'Connected (joined)';
});

sendBtn.addEventListener('click', ()=>{
  const text = msgInput.value.trim();
  if(!text) return;
  socket.emit('message', { text, username: myName });
  appendMessage({ username: 'You', text, me:true });
  msgInput.value = '';
});

chooseBtn.addEventListener('click', ()=> fileInput.click());

fileInput.addEventListener('change', ()=>{
  const f = fileInput.files[0];
  if(!f){
    fileNameLabel.textContent = 'No file chosen';
    sendFileBtn.disabled = true;
    return;
  }
  fileNameLabel.textContent = `${f.name} (${(f.size/1024).toFixed(1)} KB)`;
  sendFileBtn.disabled = false;
});

// chunked upload
sendFileBtn.addEventListener('click', async ()=>{
  const f = fileInput.files[0];
  if(!f) return alert('Choose a file');
  if(!myName) myName = usernameInput.value.trim() || ('Web' + Math.floor(Math.random()*1000));
  socket.emit('file-start', { filename: f.name, filesize: f.size, username: myName });
  uploadProgress.style.display = 'block';
  uploadProgress.max = f.size;
  uploadProgress.value = 0;

  const CHUNK = 64*1024;
  let offset = 0;
  while(offset < f.size){
    const chunk = f.slice(offset, offset + CHUNK);
    const buf = await chunk.arrayBuffer();
    let binary = '';
    const arr = new Uint8Array(buf);
    for(let i=0;i<arr.length;i++) binary += String.fromCharCode(arr[i]);
    const b64 = btoa(binary);
    socket.emit('file-chunk', { chunk_b64: b64 });
    offset += CHUNK;
    uploadProgress.value = Math.min(offset, f.size);
  }
  socket.emit('file-end', {});
  uploadProgress.style.display = 'none';
  appendMessage({ username:'You', text:`Sent file ${f.name}`, me:true });
  fileInput.value = '';
  fileNameLabel.textContent = 'No file chosen';
  sendFileBtn.disabled = true;
});

// enter to send
msgInput.addEventListener('keydown', (e)=>{
  if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); sendBtn.click(); }
});
