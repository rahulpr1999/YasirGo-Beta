import sqlite3
import time
import os
import socket
import threading
from flask import Flask, g, Response, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")
DATABASE = 'yasirgo_beta.db'
INACTIVITY_TIMEOUT = 90 * 60   # 90 minutes
EDIT_WINDOW = 5 * 60           # 5 minutes
REPORT_THRESHOLD = 5
BAN_DURATION = 24 * 60 * 60    # 24 hours

# ================== HTML_BODY ===================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YasirGo Beta</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"/>
    <script type="module" src="https://unpkg.com/emoji-picker-element"></script>
</head>
<body>
    <div id="username-modal">
        <div id="username-form">
            <video class="login-video" src="https://yasirgo.s3.eu-north-1.amazonaws.com/YasirGo-Beta-Gif+-+Made+with+Clipchamp.mp4" autoplay loop muted playsinline></video>
            <h2>YasirGo Beta</h2>
            <p>Enter a temporary name to join the secure LAN chat.</p>
            <input type="text" id="username-input" placeholder="Your name..." maxlength="15">
            <button id="join-btn">Join Chat <i class="fa-solid fa-arrow-right"></i></button>
            <p id="username-error" class="error-message"></p>
        </div>
    </div>
    <div id="app-container" class="hidden">
        <aside id="sidebar">
            <div class="sidebar-header">
                <h3>Who's Online (<span id="user-count">0</span>)</h3>
                <button id="mobile-users-close" class="mobile-only" title="Close"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <ul id="online-users-list"></ul>
            <div class="sidebar-footer">
                <button id="logout-btn"><i class="fa-solid fa-right-from-bracket"></i> Logout</button>
            </div>
        </aside>
        <main id="chat-panel">
            <header>
                <div class="header-title">
                    <video class="header-video" src="https://yasirgo.s3.eu-north-1.amazonaws.com/YasirGo-Beta-Gif+-+Made+with+Clipchamp.mp4" autoplay loop muted playsinline></video>
                    <h1>Group Chat</h1>
                </div>
                <button id="mobile-users-toggle" title="Show users" class="mobile-only">
                    <i class="fa-solid fa-users"></i>
                </button>
                <button id="theme-switcher" title="Toggle Theme">
                    <i class="fa-solid fa-sun" id="theme-sun"></i>
                    <i class="fa-solid fa-moon" id="theme-moon"></i>
                </button>
            </header>
            <div id="messages"></div>
            <div id="typing-indicator-container">
                <span id="typing-indicator"></span>
            </div>
            <footer>
                <div id="message-emoji-picker-container" class="hidden">
                    <emoji-picker class="light" id="message-emoji-picker"></emoji-picker>
                </div>
                <button id="emoji-btn" title="Emoji"><i class="fa-regular fa-face-smile"></i></button>
                <input type="text" id="message-input" placeholder="Type a message...">
                <button id="send-btn" title="Send"><i class="fa-solid fa-paper-plane"></i></button>
            </footer>
        </main>
    </div>
    <div id="reaction-emoji-picker-container" class="hidden">
        <emoji-picker class="light" id="reaction-emoji-picker"></emoji-picker>
    </div>
    <div id="report-toast" class="hidden"></div>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script src="/static/js/main.js"></script>
</body>
</html>
"""

# ================== CSS ======================
CSS_CONTENT = """
:root {
    --deep-blue: #101357; --soft-blue: #51d0de; --muted-purple: #bf4aa8;
    --subtle-green: #2ecc71; --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --bg-primary: #f0f2f5; --bg-secondary: #ffffff; --bg-tertiary: #e5e7eb;
    --text-primary: #111827; --text-secondary: #6b7280; --border-color: #d1d5db;
    --shadow-color: rgba(0, 0, 0, 0.1);
}
body.dark-mode {
    --bg-primary: #111827; --bg-secondary: #1f2937; --bg-tertiary: #374151;
    --text-primary: #f9fafb; --text-secondary: #9ca3af; --border-color: #4b5563;
    --shadow-color: rgba(0, 0, 0, 0.3);
}
body {
    font-family: var(--font-sans); background-color: var(--bg-primary); margin: 0;
    display: flex; justify-content: center; align-items: center; height: 100vh;
    color: var(--text-primary); transition: background-color 0.3s, color 0.3s;
    overflow: hidden;
}
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted-purple); }
#username-modal {
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background-color: rgba(0, 0, 0, 0.7); display: flex;
    justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(5px);
}
#username-form {
    background: var(--bg-secondary); padding: 2.5rem; border-radius: 12px; text-align: center;
    box-shadow: 0 8px 30px var(--shadow-color); animation: fadeIn 0.3s ease-out;
    width: 370px; max-width: 98vw;
}
.login-video { width: 150px; border-radius: 12px; margin-bottom: 1rem; }
#username-form h2 { color: var(--text-primary); margin-bottom: 0.5rem; }
#username-form p { color: var(--text-secondary); margin-bottom: 1.5rem; }
#username-input {
    background: var(--bg-primary); color: var(--text-primary); width: 80%; padding: 0.8rem;
    border: 1px solid var(--border-color); border-radius: 8px; font-size: 1rem; margin-bottom: 1rem;
}
#username-input:focus { border-color: var(--soft-blue); outline: none; }
#join-btn {
    background: var(--deep-blue); color: #fff; padding: 0.8rem 1.5rem; width: 100%;
    border: none; border-radius: 8px; font-size: 1rem; cursor: pointer;
    transition: background-color 0.2s, transform 0.2s;
}
#join-btn:hover { background-color: #1a1f8a; transform: translateY(-2px); }
#app-container {
    width: 95vw; height: 95vh; max-width: 1200px; max-height: 900px;
    background-color: var(--bg-secondary); border-radius: 12px;
    box-shadow: 0 5px 25px var(--shadow-color);
    display: flex; overflow: hidden; animation: zoomIn 0.4s ease-out;
}
.hidden { display: none !important; }
#sidebar {
    width: 240px; background-color: var(--bg-tertiary); display: flex;
    flex-direction: column; flex-shrink: 0; border-right: 1px solid var(--border-color);
    position: relative; transform: none; transition: none; z-index: 10;
}
.sidebar-header { padding: 1.25rem; border-bottom: 1px solid var(--border-color); position:relative; }
.sidebar-header h3 { margin: 0; font-size: 1rem; color: var(--text-primary); }
#online-users-list { list-style: none; margin: 0; padding: 1rem; overflow-y: auto; flex-grow: 1; }
#online-users-list li {
    padding: 0.5rem; color: var(--text-secondary); font-weight: 500;
    border-radius: 6px; display: flex; align-items: center; gap: 0.75rem;
}
.user-report-btn {
    background: none; border: none; color: #e67e22; cursor: pointer; font-size: 1rem; margin-left: 6px; transition: color .18s;
}
.user-report-btn:hover { color: #e74c3c; }
#online-users-list li .fa-circle { font-size: 0.6rem; color: var(--subtle-green); }
.sidebar-footer { padding: 1rem; border-top: 1px solid var(--border-color); }
#logout-btn {
    width: 100%; background-color: #e74c3c; color: white; border: none;
    padding: 0.75rem; border-radius: 8px;
    cursor: pointer; display: flex;
    align-items: center; justify-content: center; gap: 0.5rem; font-weight: 600;
}
#logout-btn:hover { background-color: #c0392b; }
#chat-panel { width: 100%; display: flex; flex-direction: column; }
#chat-panel header {
    padding: 1rem 1.5rem; background: var(--bg-secondary);
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid var(--border-color); flex-shrink: 0;
}
.header-title { display: flex; align-items: center; gap: 1rem; }
.header-video { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; }
#chat-panel header h1 { font-size: 1.2rem; margin: 0; }
#theme-switcher {
    background: none; border: none; font-size: 1.2rem; cursor: pointer;
    color: var(--text-secondary); transition: color 0.2s;
}
#theme-switcher:hover { color: var(--muted-purple); }
.fa-moon { display: none; }
body.dark-mode .fa-sun { display: none; }
body.dark-mode .fa-moon { display: inline-block; }
#messages { flex-grow: 1; overflow-y: auto; padding: 1.5rem; }
.message {
    display: flex; flex-direction: column; margin-bottom: 1rem; max-width: 75%;
    animation: slideIn 0.3s ease-out; position: relative;
}
.message-content { padding: 0.75rem 1rem; border-radius: 18px; word-wrap: break-word; }
.message-meta { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
.message-username { font-weight: 600; font-size: 0.9rem; }
.message-timestamp { font-size: 0.75rem; color: var(--text-secondary); }
.edited-tag { font-size: 0.7rem; font-style: italic; color: var(--text-secondary); margin-left: 5px; }
.message.sent { align-self: flex-end; align-items: flex-end; }
.message.sent .message-content { background-color: var(--deep-blue); color: #fff; border-bottom-right-radius: 4px; }
.message.sent .message-username { color: var(--soft-blue); }
.message.received { align-self: flex-start; align-items: flex-start; }
.message.received .message-content { background-color: var(--bg-tertiary); color: var(--text-primary); border-bottom-left-radius: 4px; }
.message.received .message-username { color: var(--muted-purple); }
.message-actions {
    display: flex; align-items: center; gap: 0.5rem;
    position: absolute; top: -15px; background-color: var(--bg-secondary);
    padding: 4px 8px; border-radius: 10px;
    box-shadow: 0 2px 5px var(--shadow-color);
    border: 1px solid var(--border-color);
    visibility: hidden; opacity: 0; transition: all 0.2s;
}
.message.sent .message-actions { right: 10px; }
.message.received .message-actions { left: 10px; }
.message:hover .message-actions { visibility: visible; opacity: 1; }
.action-btn { background: none; border: none; cursor: pointer; color: var(--text-secondary); font-size: 0.9rem; }
.action-btn:hover { color: var(--muted-purple); }
.delete-btn:hover { color: #e74c3c; }
.reactions { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }
.reaction { background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 12px;
    padding: 0.2rem 0.6rem; font-size: 0.8rem; cursor: pointer;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.reaction:hover { transform: scale(1.1); border-color: var(--soft-blue); }
footer {
    display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem;
    border-top: 1px solid var(--border-color); background-color: var(--bg-secondary); position: relative;
}
#message-input {
    flex-grow: 1; border: none; background: var(--bg-tertiary); color: var(--text-primary);
    border-radius: 20px; padding: 0.85rem 1.25rem; font-size: 1rem;
}
#message-input:focus { outline: none; box-shadow: 0 0 0 2px var(--soft-blue); }
#emoji-btn, #send-btn {
    background: none; border: none; font-size: 1.5rem; cursor: pointer;
    color: var(--text-secondary); padding: 0.5rem; transition: color 0.2s;
}
#emoji-btn:hover { color: var(--muted-purple);}
#send-btn:hover { color: var(--deep-blue);}
body.dark-mode #send-btn:hover { color: var(--soft-blue);}
#message-emoji-picker-container { position: absolute; bottom: 75px; left: 1rem; z-index: 50; }
#reaction-emoji-picker-container { position: absolute; z-index: 60; }
emoji-picker {
    --border-color: var(--border-color); --shadow: 0 5px 15px var(--shadow-color);
    border: 1px solid var(--border-color);
}
#typing-indicator-container {
    min-height: 1.5rem;
    height: auto;
    padding: 0 1.5rem;
    display: block;
    box-sizing: border-box;
}
.edit-input-container { display: flex; gap: 5px; margin-top: 5px; }
.edit-input { flex-grow: 1; padding: 5px; border-radius: 5px; border: 1px solid var(--border-color); background: var(--bg-tertiary); color: var(--text-primary); }
.edit-save-btn { background-color: var(--subtle-green); color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; }
#report-toast {
    position: fixed; left: 0; right: 0; bottom: 2rem;
    margin: auto; z-index: 1099; width: fit-content;
    min-width: 180px; max-width: 95vw;
    background: var(--deep-blue); color: #fff; padding: 1em 1.4em; border-radius: 10px;
    box-shadow: 0 6px 20px var(--shadow-color); text-align: center; font-weight: 500;
    transition: opacity .25s;
}
.mobile-only { display: none; }
@media (max-width: 768px) {
    .mobile-only { display: inline-block !important;}
    #sidebar {
        position: fixed;
        top: 0; left: 0;
        width: 80vw; max-width: 340px;
        height: 100vh; max-height: none;
        background: var(--bg-tertiary);
        z-index: 200;
        transform: translateX(-100%);
        transition: transform 0.3s;
        box-shadow: 0 6px 24px var(--shadow-color);
        border-right: 1px solid var(--border-color);
        border-radius: 0 10px 10px 0;
        display: block;
    }
    #sidebar.open {
        transform: translateX(0);
        pointer-events: auto;
    }
    #sidebar:not(.open) {
        pointer-events: none;
        z-index: 0;
    }
    .sidebar-header { position: relative; }
    #mobile-users-close {
        position: absolute;
        right: 0.5em;
        top: 0.5em;
        background: transparent;
        border: none;
        color: var(--text-secondary);
        font-size: 1.3em;
        z-index: 10;
    }
    #app-container { flex-direction: column; }
    .sidebar-footer { display: none !important; }
    #mobile-users-toggle { margin-left: auto; margin-right: 16px;}
}
@media (max-width: 500px) {
    #username-form { width: 96vw; padding: 1.2rem 0.6rem; box-sizing: border-box; }
    .login-video { width: 110px; }
    #app-container { width: 100vw; height: 100vh; border-radius: 0; min-width: unset; min-height: unset;}
    #sidebar { width: 88vw; max-width: none; }
    #reaction-emoji-picker-container, #message-emoji-picker-container { left: 0.5rem!important;}
    #messages, #online-users-list { padding: 0.5rem!important;}
}
@media (max-width: 350px) {
    #username-form { padding: 0.7rem 0.2rem;}
    .login-video { width: 80px; }
    #sidebar { width: 95vw; }
}
@media (min-width: 769px) {
    #sidebar { position: relative; transform: none !important; width: 240px; height: auto; }
    .mobile-only { display: none !important; }
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes zoomIn { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
@keyframes slideIn { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
"""

# ============== Full main.js ==============
JS_CONTENT = """
document.addEventListener('DOMContentLoaded', () => {
    const usernameModal = document.getElementById('username-modal');
    const usernameInput = document.getElementById('username-input');
    const joinBtn = document.getElementById('join-btn');
    const usernameError = document.getElementById('username-error');
    const appContainer = document.getElementById('app-container');
    const messagesDiv = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const onlineUsersList = document.getElementById('online-users-list');
    const userCountSpan = document.getElementById('user-count');
    const typingIndicator = document.getElementById('typing-indicator');
    const themeSwitcher = document.getElementById('theme-switcher');
    const logoutBtn = document.getElementById('logout-btn');
    const messageEmojiBtn = document.getElementById('emoji-btn');
    const messageEmojiPickerContainer = document.getElementById('message-emoji-picker-container');
    const messageEmojiPicker = document.getElementById('message-emoji-picker');
    const reactionEmojiPickerContainer = document.getElementById('reaction-emoji-picker-container');
    const reactionEmojiPicker = document.getElementById('reaction-emoji-picker');
    const mobileUsersToggle = document.getElementById('mobile-users-toggle');
    const mobileUsersClose = document.getElementById('mobile-users-close');
    const sidebar = document.getElementById('sidebar');
    const themeSun = document.getElementById('theme-sun');
    const themeMoon = document.getElementById('theme-moon');
    const reportToast = document.getElementById('report-toast');
    let username = localStorage.getItem('yasirgo_beta_username');
    let typingTimeout;

    // Responsive: input (on any change) for real time typing
    messageInput.addEventListener('input', handleTyping);

    function setThemeIcon(theme) {
        if (theme === "dark") {
            themeSun.style.display = "none";
            themeMoon.style.display = "";
        } else {
            themeSun.style.display = "";
            themeMoon.style.display = "none";
        }
    }
    const applyTheme = (theme) => {
        document.body.classList.toggle('dark-mode', theme === 'dark');
        messageEmojiPicker.classList.toggle('dark', theme === 'dark');
        reactionEmojiPicker.classList.toggle('dark', theme === 'dark');
        setThemeIcon(theme);
    };
    let currentTheme = localStorage.getItem('yasirgo_beta_theme') || 'light';
    applyTheme(currentTheme);

    const socket = io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
        username = localStorage.getItem('yasirgo_beta_username');
        if (username) {
            socket.emit('rejoin', { username });
        } else {
            showUsernameModal();
        }
    });

    function showUsernameModal() { appContainer.classList.add('hidden'); usernameModal.style.display = 'flex'; }
    function hideUsernameModal() { usernameModal.style.display = 'none'; appContainer.classList.remove('hidden'); messageInput.focus(); }
    function joinChat() {
        const chosenUsername = usernameInput.value.trim();
        if (!chosenUsername) {
            usernameError.textContent = 'Username cannot be empty.';
            return;
        }
        socket.emit('join', { username: chosenUsername });
    }
    function sendMessage() {
        const content = messageInput.value.trim();
        if (!content) return;
        const myUsername = localStorage.getItem('yasirgo_beta_username');
        if (!myUsername) return;
        socket.emit('send_message', { username: myUsername, content });
        messageInput.value = '';
    }
    function handleTyping() {
        clearTimeout(typingTimeout);
        const myUsername = localStorage.getItem('yasirgo_beta_username');
        if (!myUsername) return;
        socket.emit('typing', { username: myUsername, is_typing: true });
        typingTimeout = setTimeout(() => {
            socket.emit('typing', { username: myUsername, is_typing: false });
        }, 3000);
    }
    function handleMessageAction(e) {
        const target = e.target.closest('.action-btn, .reaction');
        if (!target) return;
        const messageElement = target.closest('.message');
        const messageId = messageElement.dataset.id;
        if (target.classList.contains('delete-btn')) {
            socket.emit('delete_message', { username, message_id: messageId });
        } else if (target.classList.contains('reply-btn')) {
            const userToReply = messageElement.querySelector('.message-username').textContent;
            messageInput.value += `@${userToReply} `;
            messageInput.focus();
        } else if (target.classList.contains('react-btn')) {
            reactionEmojiPickerContainer.classList.remove('hidden');
            const rect = target.getBoundingClientRect();
            let top = rect.top - 450;
            if (top < 10) top = rect.bottom + 10;
            let left = rect.left - 150;
            if (left < 10) left = 10;
            reactionEmojiPickerContainer.style.top = `${top}px`;
            reactionEmojiPickerContainer.style.left = `${left}px`;
            reactionEmojiPickerContainer.dataset.messageId = messageId;
        } else if (target.classList.contains('edit-btn')) {
            enterEditMode(messageElement);
        } else if (target.classList.contains('reaction')) {
            socket.emit('react', { username, message_id: messageId, emoji: target.dataset.emoji });
        }
    }
    function enterEditMode(messageElement) {
        const contentDiv = messageElement.querySelector('.message-content');
        if (!contentDiv || messageElement.querySelector('.edit-input')) return;
        const currentText = contentDiv.textContent.trim();
        contentDiv.style.display = 'none';
        const editContainer = document.createElement('div');
        editContainer.className = 'edit-input-container';
        editContainer.innerHTML = `
            <input type="text" class="edit-input" value="${currentText}">
            <button class="edit-save-btn">Save</button>
        `;
        contentDiv.parentElement.insertBefore(editContainer, contentDiv.nextSibling);
        const editInput = editContainer.querySelector('.edit-input');
        editInput.focus();
        const saveEdit = () => {
            const newContent = editInput.value.trim();
            if (newContent && newContent !== currentText) {
                socket.emit('edit_message', { 
                    username, 
                    message_id: messageElement.dataset.id, 
                    new_content: newContent 
                });
            }
            exitEditMode(messageElement);
        };
        editContainer.querySelector('.edit-save-btn').addEventListener('click', saveEdit);
        editInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') saveEdit();
        });
        editInput.addEventListener('blur', () => {
            setTimeout(() => exitEditMode(messageElement), 100);
        });
    }
    function exitEditMode(messageElement) {
        const contentDiv = messageElement.querySelector('.message-content');
        const editContainer = messageElement.querySelector('.edit-input-container');
        if (editContainer) {
            editContainer.remove();
        }
        if (contentDiv) {
            contentDiv.style.display = 'block';
        }
    }
    socket.on('join_success', (data) => {
        username = data.username;
        localStorage.setItem('yasirgo_beta_username', username);
        hideUsernameModal();
    });
    socket.on('join_error', (data) => { usernameError.textContent = data.message; });
    socket.on('rejoin_failed', () => { localStorage.removeItem('yasirgo_beta_username'); showUsernameModal(); });
    socket.on('chat_update', (data) => {
        renderMessages(data.messages);
        renderOnlineUsers(data.online_users);
        renderTypingIndicator(data.typing_users);
    });
    function renderMessages(messages) {
        const wasScrolledToBottom = messagesDiv.scrollHeight - messagesDiv.clientHeight <= messagesDiv.scrollTop + 50;
        let lastDate = null;
        messagesDiv.innerHTML = '';
        messages.forEach(msg => {
            const messageDate = new Date(msg.timestamp * 1000);
            const messageDateString = messageDate.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' });
            if (messageDateString !== lastDate) {
                messagesDiv.insertAdjacentHTML('beforeend', `<div class="date-header">${messageDateString}</div>`);
                lastDate = messageDateString;
            }
            const reactionsHTML = (msg.reactions || []).map(r =>
                `<div class="reaction" data-emoji="${r.emoji}" title="${r.users.join(', ')}">${r.emoji} ${r.count}</div>`
            ).join('');
            const isEditable = msg.username === username && (Date.now() / 1000 - msg.timestamp < 5 * 60);
            const editedTag = msg.is_edited ? '<span class="edited-tag">(edited)</span>' : '';
            const messageHTML = `
                <div class="message ${msg.username === username ? 'sent' : 'received'}" data-id="${msg.id}">
                    <div class="message-meta">
                        <span class="message-username">${msg.username}</span>
                        <span class="message-timestamp">${messageDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ${editedTag}</span>
                    </div>
                    <div class="message-content">${formatMessageContent(msg.content)}</div>
                    <div class="reactions">${reactionsHTML}</div>
                    <div class="message-actions">
                        <button class="action-btn reply-btn" title="Reply"><i class="fa-solid fa-reply"></i></button>
                        <button class="action-btn react-btn" title="React"><i class="fa-regular fa-face-laugh"></i></button>
                        ${isEditable ? `<button class="action-btn edit-btn" title="Edit"><i class="fa-solid fa-pencil"></i></button>` : ''}
                        ${msg.username === username ? `<button class="action-btn delete-btn" title="Delete"><i class="fa-regular fa-trash-can"></i></button>` : ''}
                    </div>
                </div>`;
            messagesDiv.insertAdjacentHTML('beforeend', messageHTML);
        });
        if (wasScrolledToBottom) messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    function renderOnlineUsers(users) {
        userCountSpan.textContent = users.length;
        let myUsername = localStorage.getItem('yasirgo_beta_username');
        onlineUsersList.innerHTML = users.map(user => `
            <li${user===myUsername?' style="font-weight:600"':''}>
              <i class="fa-solid fa-circle"></i>
              ${user}
              ${user !== myUsername ? `<button class="user-report-btn" data-user="${user}" title="Report this user"><i class="fa-solid fa-triangle-exclamation"></i></button>` : ''}
            </li>`
        ).join('');
    }
    function renderTypingIndicator(typingUsernames) {
        const me = localStorage.getItem('yasirgo_beta_username');
        const othersTyping = typingUsernames.filter(u => u && u !== me);
        if (othersTyping.length === 0) {
            typingIndicator.textContent = '';
        } else if (othersTyping.length === 1) {
            typingIndicator.textContent = `${othersTyping[0]} is typing...`;
        } else {
            typingIndicator.textContent = `${othersTyping.join(', ')} are typing...`;
        }
    }
    function formatMessageContent(content) {
        return content.replace(/(@[a-zA-Z0-9_]+)/g, '<strong>$1</strong>');
    }
    themeSwitcher.addEventListener('click', () => {
        currentTheme = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
        localStorage.setItem('yasirgo_beta_theme', currentTheme);
        applyTheme(currentTheme);
    });
    document.addEventListener('click', (e) => {
        if (!messageEmojiPickerContainer.contains(e.target) && e.target !== messageEmojiBtn) {
            messageEmojiPickerContainer.classList.add('hidden');
        }
        if (!reactionEmojiPickerContainer.contains(e.target) && !e.target.closest('.react-btn')) {
            reactionEmojiPickerContainer.classList.add('hidden');
        }
    });
    joinBtn.addEventListener('click', joinChat);
    usernameInput.addEventListener('keypress', (e) => e.key === 'Enter' && joinChat());
    sendBtn.addEventListener('click', sendMessage);
    // messageInput.addEventListener('keypress', (e) => { ... old typing ... }); // replaced by input
    messageEmojiBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        reactionEmojiPickerContainer.classList.add('hidden');
        messageEmojiPickerContainer.classList.toggle('hidden');
    });
    messageEmojiPicker.addEventListener('emoji-click', event => {
        messageInput.value += event.detail.emoji.unicode;
        messageInput.focus();
    });
    reactionEmojiPicker.addEventListener('emoji-click', event => {
        const messageId = reactionEmojiPickerContainer.dataset.messageId;
        if (messageId) {
            socket.emit('react', { username, message_id: messageId, emoji: event.detail.emoji.unicode });
        }
        reactionEmojiPickerContainer.classList.add('hidden');
    });
    logoutBtn.addEventListener('click', () => {
        if (username) {
            socket.emit('logout', { username });
            localStorage.removeItem('yasirgo_beta_username');
            window.location.reload();
        }
    });
    messagesDiv.addEventListener('click', handleMessageAction);

    // MOBILE SIDEBAR SHOW/HIDE LOGIC FOR USERS LIST
    mobileUsersToggle.addEventListener('click', function(e) {
        sidebar.classList.add('open');
        document.body.style.overflow = 'hidden';
    });
    mobileUsersClose.addEventListener('click', function(e) {
        sidebar.classList.remove('open');
        document.body.style.overflow = '';
    });
    document.addEventListener('click', function(e) {
        if (window.innerWidth <= 768) {
            if (sidebar.classList.contains('open') &&
                !sidebar.contains(e.target) &&
                !mobileUsersToggle.contains(e.target)) {
                sidebar.classList.remove('open');
                document.body.style.overflow = '';
            }
        }
    });
    sidebar.addEventListener('click', function(e) { e.stopPropagation(); });

    // Handle reporting
    onlineUsersList.addEventListener('click', function(ev) {
        const btn = ev.target.closest('.user-report-btn');
        if (!btn) return;
        const reported = btn.getAttribute('data-user');
        if (!reported) return;
        socket.emit('report_user', { 
            reported_username: reported, 
            reporter_username: localStorage.getItem('yasirgo_beta_username') 
        });
    });
    socket.on('user_banned', function(data){
        showToast(`${data.username} has been banned for 24hr.`);
        if (data.username === localStorage.getItem('yasirgo_beta_username')) {
            setTimeout(()=>{window.location.reload();},1200);
        }
    });
    socket.on('report_result', function(res){
        showToast(res.message, res.success ? 'success' : 'fail');
    });
    function showToast(msg, type) {
        reportToast.textContent = msg;
        reportToast.className = "";
        reportToast.classList.add(type==='fail'?'fail':'');
        reportToast.classList.remove('hidden');
        setTimeout(()=>{ reportToast.classList.add('hidden'); }, 2800);
    }
});
"""

# --- DB + Flask backend as in previous code ---

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        schema = """
            CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, last_active INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY, 
                username TEXT, 
                content TEXT, 
                timestamp INTEGER,
                is_edited INTEGER DEFAULT 0 NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reactions (id INTEGER PRIMARY KEY, message_id INTEGER, username TEXT, emoji TEXT, FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE, UNIQUE(message_id, username, emoji));
            CREATE TABLE IF NOT EXISTS typing_status (username TEXT PRIMARY KEY, timestamp INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY, reported_username TEXT, reporter_username TEXT, reporter_ip TEXT, timestamp INTEGER);
            CREATE TABLE IF NOT EXISTS bans (username TEXT, ip TEXT, banned_until INTEGER);
        """
        db.cursor().executescript(schema)
        db.commit()

def cleanup_expired_data():
    with app.app_context():
        db = get_db()
        now = int(time.time())
        expiry_time = now - INACTIVITY_TIMEOUT
        db.execute('DELETE FROM users WHERE last_active < ?', (expiry_time,))
        db.execute('DELETE FROM messages WHERE timestamp < ?', (expiry_time,))
        db.execute('DELETE FROM typing_status WHERE timestamp < ?', (now - 5,))
        db.execute('DELETE FROM bans WHERE banned_until < ?', (now,))
        db.commit()

def background_scheduler():
    while True:
        cleanup_expired_data()
        time.sleep(300)

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    return request.remote_addr or "unknown"

def is_banned(username, ip):
    db = get_db()
    now = int(time.time())
    return bool(db.execute("SELECT 1 FROM bans WHERE (username = ? OR ip = ?) AND banned_until > ?", (username, ip, now)).fetchone())

def set_ban(username, ip):
    now = int(time.time())
    banned_until = now + BAN_DURATION
    db = get_db()
    db.execute("INSERT INTO bans (username, ip, banned_until) VALUES (?, ?, ?)", (username, ip, banned_until))
    db.commit()

def get_all_chat_data():
    db = get_db()
    messages_rows = db.execute('SELECT id, username, content, timestamp, is_edited FROM messages ORDER BY timestamp ASC').fetchall()
    messages = [dict(row) for row in messages_rows]
    message_ids = [msg['id'] for msg in messages]
    reactions_dict = {}
    if message_ids:
        placeholders = ','.join('?' for _ in message_ids)
        reactions_rows = db.execute(f'SELECT * FROM reactions WHERE message_id IN ({placeholders})', message_ids).fetchall()
        for r in reactions_rows:
            msg_id = r['message_id']
            if msg_id not in reactions_dict: reactions_dict[msg_id] = {}
            if r['emoji'] not in reactions_dict[msg_id]:
                reactions_dict[msg_id][r['emoji']] = {'count': 0, 'users': []}
            reactions_dict[msg_id][r['emoji']]['count'] += 1
            reactions_dict[msg_id][r['emoji']]['users'].append(r['username'])
    for msg in messages:
        msg_reactions = reactions_dict.get(msg['id'], {})
        msg['reactions'] = [{'emoji': emoji, **data} for emoji, data in msg_reactions.items()]
    online_users = [row['username'] for row in db.execute('SELECT username FROM users ORDER BY username').fetchall()]
    typing_users = [row['username'] for row in db.execute('SELECT username FROM typing_status').fetchall()]
    return {'messages': messages, 'online_users': online_users, 'typing_users': typing_users}

@app.route('/')
def index(): return render_template_string(HTML_CONTENT)
@app.route('/static/css/style.css')
def serve_css(): return Response(CSS_CONTENT, mimetype='text/css')
@app.route('/static/js/main.js')
def serve_js(): return Response(JS_CONTENT, mimetype='application/javascript')

def broadcast_update():
    socketio.emit('chat_update', get_all_chat_data())

@socketio.on('join')
def handle_join(data):
    username = data.get('username').strip()[:32]
    ip = get_client_ip()
    db = get_db()
    now = int(time.time())
    if is_banned(username, ip):
        emit('join_error', {'message': 'You are banned for 24 hours.'})
        return
    if db.execute('SELECT 1 FROM users WHERE username = ?', (username,)).fetchone():
        emit('join_error', {'message': 'Username is already taken.'})
        return
    db.execute('INSERT OR REPLACE INTO users (username, last_active) VALUES (?, ?)', (username, now))
    db.commit()
    emit('join_success', {'username': username})
    broadcast_update()

@socketio.on('rejoin')
def handle_rejoin(data):
    username = data.get('username').strip()[:32]
    ip = get_client_ip()
    db = get_db()
    if is_banned(username, ip):
        emit('rejoin_failed')
        return
    db.execute('INSERT OR REPLACE INTO users (username, last_active) VALUES (?, ?)', (username, int(time.time())))
    db.commit()
    emit('join_success', {'username': username})
    broadcast_update()

@socketio.on('logout')
def handle_logout(data):
    username = data.get('username')
    db = get_db()
    db.execute('DELETE FROM users WHERE username = ?', (username,))
    db.execute('DELETE FROM typing_status WHERE username = ?', (username,))
    db.commit()
    broadcast_update()

@socketio.on('send_message')
def handle_send_message(data):
    username, content = data.get('username'), data.get('content')
    db = get_db()
    db.execute('INSERT INTO messages (username, content, timestamp) VALUES (?, ?, ?)', (username, content, int(time.time())))
    db.execute('UPDATE users SET last_active = ? WHERE username = ?', (int(time.time()), username))
    db.commit()
    broadcast_update()

@socketio.on('delete_message')
def handle_delete_message(data):
    username, message_id = data.get('username'), data.get('message_id')
    db = get_db()
    msg = db.execute('SELECT 1 FROM messages WHERE id = ? AND username = ?', (message_id, username)).fetchone()
    if msg:
        db.execute('DELETE FROM messages WHERE id = ?', (message_id,))
        db.commit()
        broadcast_update()

@socketio.on('edit_message')
def handle_edit_message(data):
    username, message_id, new_content = data.get('username'), data.get('message_id'), data.get('new_content')
    db = get_db()
    msg = db.execute('SELECT timestamp FROM messages WHERE id = ? AND username = ?', (message_id, username)).fetchone()
    if msg and (int(time.time()) - msg['timestamp'] <= EDIT_WINDOW):
        db.execute('UPDATE messages SET content = ?, is_edited = 1 WHERE id = ?', (new_content, message_id))
        db.commit()
        broadcast_update()

@socketio.on('react')
def handle_react(data):
    username, message_id, emoji = data.get('username'), data.get('message_id'), data.get('emoji')
    db = get_db()
    existing = db.execute('SELECT id FROM reactions WHERE message_id = ? AND username = ? AND emoji = ?', (message_id, username, emoji)).fetchone()
    if existing:
        db.execute('DELETE FROM reactions WHERE id = ?', (existing['id'],))
    else:
        db.execute('INSERT INTO reactions (message_id, username, emoji) VALUES (?, ?, ?)', (message_id, username, emoji))
    db.commit()
    broadcast_update()

@socketio.on('typing')
def handle_typing(data):
    username, is_typing = data.get('username'), data.get('is_typing')
    db = get_db()
    now = int(time.time())
    if is_typing:
        db.execute('REPLACE INTO typing_status (username, timestamp) VALUES (?, ?)', (username, now))
    else:
        db.execute('DELETE FROM typing_status WHERE username = ?', (username,))
    db.commit()
    broadcast_update()  # send real-time typing status

@socketio.on('report_user')
def handle_report_user(data):
    reported_username = data.get('reported_username')
    reporter_username = data.get('reporter_username')
    reporter_ip = get_client_ip()
    now = int(time.time())
    db = get_db()
    if reported_username == reporter_username:
        emit('report_result', {'success': False, 'message': "You cannot report yourself."})
        return
    if is_banned(reported_username, reporter_ip):
        emit('report_result', {'success': False, 'message': "This user is already banned."})
        return
    twentyfour_ago = now - BAN_DURATION
    dup = db.execute("""SELECT 1 FROM reports WHERE reported_username=? AND reporter_ip=? AND timestamp>?""",
                     (reported_username, reporter_ip, twentyfour_ago)).fetchone()
    if dup:
        emit('report_result', {'success': False, 'message': "You have already reported this user in the last 24hr."})
        return
    db.execute('INSERT INTO reports (reported_username, reporter_username, reporter_ip, timestamp) VALUES (?, ?, ?, ?)',
               (reported_username, reporter_username, reporter_ip, now))
    db.commit()
    row = db.execute("""SELECT COUNT(DISTINCT reporter_ip) AS num FROM reports 
                        WHERE reported_username=? AND timestamp>?""", (reported_username, twentyfour_ago)).fetchone()
    if row and row['num'] >= REPORT_THRESHOLD:
        ips = db.execute("""SELECT DISTINCT reporter_ip FROM reports 
                            WHERE reported_username=? AND timestamp>?""", (reported_username, twentyfour_ago)).fetchall()
        set_ban(reported_username, None)
        for iprow in ips:
            set_ban(None, iprow['reporter_ip'])
        socketio.emit('user_banned', {'username': reported_username, 'banned_for': BAN_DURATION})
        emit('report_result', {'success': True, 'message': "User banned for 24hr."})
        return
    emit('report_result', {'success': True, 'message': f"Report submitted. {REPORT_THRESHOLD - row['num']} more reports needed to ban."})

@socketio.on('connect')
def handle_connect():
    emit('chat_update', get_all_chat_data())

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("First run: Creating database...")
        init_db()
    cleanup_thread = threading.Thread(target=background_scheduler, daemon=True)
    cleanup_thread.start()
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        host_ip = '127.0.0.1'
    print("--- YasirGo Beta Server ---")
    print(f"Access from any device on this LAN at: http://{host_ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000)
