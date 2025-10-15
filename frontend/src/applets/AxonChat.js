// Axon BBS - A modern, anonymous, federated bulletin board system.
// Copyright (C) 2025 Achduke7
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// Full path: axon_bbs/frontend/src/applets/AxonChat.js

// --- Start of Applet API Helper (MANDATORY) ---
window.bbs = {
  _callbacks: {},
  _requestId: 0,
  _handleMessage: function(event) {
    const { command, payload, requestId, error } = event.data;
    if (command && command.startsWith('response_') && this._callbacks[requestId]) {
      const { resolve, reject } = this._callbacks[requestId];
      if (error) { reject(new Error(error)); } else { resolve(payload); }
      delete this._callbacks[requestId];
    }
  },
  _postMessage: function(command, payload = {}) {
    return new Promise((resolve, reject) => {
      const requestId = this._requestId++;
      this._callbacks[requestId] = { resolve, reject };
      if (window.parent !== window) {
        window.parent.postMessage({ command, payload, requestId }, '*');
      } else {
        console.warn("BBS API: Not running in a frame. Call will be simulated.");
        if(command === 'getUser Info') {
          resolve({ id: 'SIMULATED_ID', name: 'AxonChat', parameters: {} });
        } else {
          resolve({});
        }
      }
    });
  },
  // Standard API
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); },
  // Advanced API
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); },
  fetch: function(url, options = {}) {
    return this._postMessage('fetch', { url, options }).then(response => response);
  }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    const appletContainer = document.getElementById('applet-root');

    // Debug console helper
    function debugLog(message) {
        console.log(`[AxonChat] ${message}`);
        if (window.BBS_DEBUG_MODE !== true) return;
        const debugDialog = document.getElementById('debug-dialog');
        if (!debugDialog) return;
        const logEntry = document.createElement('div');
        const timestamp = new Date().toLocaleTimeString();
        logEntry.textContent = `[${timestamp}] ${message}`;
        debugDialog.appendChild(logEntry);
        debugDialog.scrollTop = debugDialog.scrollHeight;
    }

    try {
        debugLog("Starting AxonChat initialization...");

        // Get applet info and user info
        debugLog("Fetching applet info...");
        const appletInfo = await window.bbs.getAppletInfo();
        debugLog(`Applet info received: ${JSON.stringify(appletInfo)}`);

        debugLog("Fetching user info...");
        const userInfo = await window.bbs.getUserInfo();
        debugLog(`User info received: nickname=${userInfo.nickname}, pubkey=${userInfo.pubkey}, avatar=${userInfo.avatar_url}`);

        const appletId = appletInfo.id;

        // Render UI
        const htmlContent = `
            <style>
                body, html {
                    margin: 0;
                    padding: 0;
                    overflow: hidden;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background-color: #1a1a2e;
                    color: #eee;
                }
                #chat-main-container {
                    display: flex;
                    height: 100vh;
                }
                #user-sidebar {
                    width: 200px;
                    background-color: #16213e;
                    border-right: 2px solid #0f3460;
                    display: flex;
                    flex-direction: column;
                    overflow-y: auto;
                }
                #user-sidebar-header {
                    padding: 15px;
                    background-color: #0f3460;
                    font-weight: bold;
                    border-bottom: 2px solid #1a1a2e;
                    text-align: center;
                }
                .user-item {
                    display: flex;
                    align-items: center;
                    padding: 10px;
                    border-bottom: 1px solid #0f3460;
                    transition: background-color 0.2s;
                }
                .user-item:hover {
                    background-color: #1a1a2e;
                }
                .user-avatar {
                    width: 32px;
                    height: 32px;
                    border-radius: 50%;
                    margin-right: 10px;
                    border: 2px solid #53a8b6;
                }
                .user-nickname {
                    font-size: 0.9em;
                    color: #eee;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                #chat-container {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                }
                #chat-header {
                    background-color: #16213e;
                    padding: 15px 20px;
                    border-bottom: 2px solid #0f3460;
                    font-size: 1.2em;
                    font-weight: bold;
                }
                #chat-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 20px;
                    background-color: #1a1a2e;
                }
                .chat-message {
                    margin-bottom: 12px;
                    padding: 10px 15px;
                    background-color: #16213e;
                    border-radius: 8px;
                    border-left: 3px solid #0f3460;
                    animation: slideIn 0.3s ease-out;
                }
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(10px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                .chat-message .timestamp {
                    color: #888;
                    font-size: 0.85em;
                    margin-right: 8px;
                }
                .chat-message .user {
                    color: #53a8b6;
                    font-weight: bold;
                    margin-right: 8px;
                }
                .chat-message .text {
                    color: #eee;
                    word-wrap: break-word;
                }
                #chat-input-area {
                    display: flex;
                    padding: 15px 20px;
                    background-color: #16213e;
                    border-top: 2px solid #0f3460;
                }
                #chat-input {
                    flex: 1;
                    padding: 12px 15px;
                    border: 2px solid #0f3460;
                    border-radius: 8px;
                    background-color: #1a1a2e;
                    color: #eee;
                    font-size: 1em;
                    outline: none;
                    transition: border-color 0.2s;
                }
                #chat-input:focus {
                    border-color: #53a8b6;
                }
                #chat-send {
                    margin-left: 10px;
                    padding: 12px 25px;
                    background-color: #0f3460;
                    color: #eee;
                    border: none;
                    border-radius: 8px;
                    font-size: 1em;
                    font-weight: bold;
                    cursor: pointer;
                    transition: background-color 0.2s;
                }
                #chat-send:hover {
                    background-color: #53a8b6;
                }
                #chat-send:active {
                    background-color: #469aa8;
                }
                #connection-status {
                    padding: 8px 20px;
                    background-color: #2d4a5a;
                    text-align: center;
                    font-size: 0.9em;
                    color: #aaa;
                }
                #connection-status.connected {
                    background-color: #1b4332;
                    color: #95d5b2;
                }
                #connection-status.disconnected {
                    background-color: #582f0e;
                    color: #ffb700;
                }
                #debug-dialog {
                    display: none;
                    position: absolute;
                    bottom: 10px;
                    right: 10px;
                    width: 400px;
                    height: 300px;
                    background-color: rgba(0, 0, 0, 0.9);
                    border: 1px solid #4a5568;
                    border-radius: 5px;
                    color: #9AE6B4;
                    font-family: monospace;
                    font-size: 11px;
                    overflow-y: scroll;
                    padding-top: 25px;
                    z-index: 1000;
                }
                #debug-header {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    background-color: #4a5568;
                    color: white;
                    font-weight: bold;
                    padding: 5px;
                    cursor: move;
                    user-select: none;
                    text-align: center;
                }
                #debug-dialog div {
                    padding: 2px 5px;
                    word-wrap: break-word;
                }
            </style>
            <div id="debug-dialog">
                <div id="debug-header">AXONCHAT DEBUG CONSOLE</div>
            </div>
            <div id="chat-main-container">
                <div id="user-sidebar">
                    <div id="user-sidebar-header">Users Online</div>
                    <div id="user-list"></div>
                </div>
                <div id="chat-container">
                    <div id="chat-header">AxonChat - Federated Chat</div>
                    <div id="connection-status" class="disconnected">Connecting...</div>
                    <div id="chat-messages"></div>
                    <div id="chat-input-area">
                        <input type="text" id="chat-input" placeholder="Type a message..." autocomplete="off">
                        <button id="chat-send">Send</button>
                    </div>
                </div>
            </div>
        `;
        appletContainer.innerHTML = htmlContent;

        // Make debug console draggable and visible if debug mode is enabled
        if (window.BBS_DEBUG_MODE === true) {
            const debugDialog = document.getElementById('debug-dialog');
            debugDialog.style.display = 'block';
            const debugHeader = document.getElementById('debug-header');
            let isDragging = false, offsetX, offsetY;
            debugHeader.onmousedown = (e) => {
                isDragging = true;
                offsetX = e.clientX - debugDialog.offsetLeft;
                offsetY = e.clientY - debugDialog.offsetTop;
            };
            document.onmousemove = (e) => {
                if (isDragging) {
                    debugDialog.style.left = `${e.clientX - offsetX}px`;
                    debugDialog.style.top = `${e.clientY - offsetY}px`;
                    debugDialog.style.bottom = 'auto';
                    debugDialog.style.right = 'auto';
                }
            };
            document.onmouseup = () => { isDragging = false; };
        }

        debugLog("UI rendered successfully");

        // State management
        let currentMessages = [];
        let activeUsers = new Map(); // Map of user short ID -> { nickname, avatar, lastSeen }
        let eventSource = null;

        // Always add current user to active users list
        const currentUserShortId = userInfo.pubkey.substring(0, 16);
        activeUsers.set(currentUserShortId, {
            nickname: userInfo.nickname || currentUserShortId,
            avatar: userInfo.avatar_url || `/media/avatars/default_cow_${currentUserShortId}.png`,
            lastSeen: Date.now()
        });
        debugLog(`Added current user to sidebar: ${currentUserShortId}`);

        // Extract unique users from messages
        function updateActiveUsers(messages) {
            const now = Date.now();
            const activeThreshold = 5 * 60 * 1000; // 5 minutes

            // Always keep current user in the list
            if (!activeUsers.has(currentUserShortId)) {
                activeUsers.set(currentUserShortId, {
                    nickname: userInfo.nickname || currentUserShortId,
                    avatar: userInfo.avatar_url || `/media/avatars/default_cow_${currentUserShortId}.png`,
                    lastSeen: now
                });
            }

            // Update from recent messages
            messages.forEach(msg => {
                const timestamp = new Date(msg.timestamp).getTime();
                if (now - timestamp < activeThreshold) {
                    if (!activeUsers.has(msg.user)) {
                        activeUsers.set(msg.user, {
                            nickname: msg.user,
                            avatar: `/media/avatars/default_cow_${msg.user}.png`, // Default avatar
                            lastSeen: timestamp
                        });
                    } else {
                        activeUsers.get(msg.user).lastSeen = timestamp;
                    }
                }
            });

            // Remove inactive users (but never remove current user)
            for (const [userId, userData] of activeUsers.entries()) {
                if (userId !== currentUserShortId && now - userData.lastSeen > activeThreshold) {
                    activeUsers.delete(userId);
                }
            }

            renderUserList();
        }

        // Render user list
        function renderUserList() {
            const userListContainer = document.getElementById('user-list');
            userListContainer.innerHTML = '';

            const sortedUsers = Array.from(activeUsers.entries()).sort((a, b) => {
                // Current user always at the top
                if (a[0] === currentUserShortId) return -1;
                if (b[0] === currentUserShortId) return 1;
                return a[1].nickname.localeCompare(b[1].nickname);
            });

            sortedUsers.forEach(([userId, userData]) => {
                const userItem = document.createElement('div');
                userItem.className = 'user-item';

                const avatar = document.createElement('img');
                avatar.className = 'user-avatar';
                avatar.src = userData.avatar;
                avatar.alt = userData.nickname;
                avatar.onerror = function() {
                    // Fallback to generated avatar
                    this.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect fill="%2353a8b6" width="32" height="32"/><text x="16" y="20" text-anchor="middle" fill="white" font-size="14">' + userData.nickname[0] + '</text></svg>';
                };

                const nickname = document.createElement('div');
                nickname.className = 'user-nickname';
                nickname.textContent = userData.nickname + (userId === currentUserShortId ? ' (You)' : '');

                userItem.appendChild(avatar);
                userItem.appendChild(nickname);
                userListContainer.appendChild(userItem);
            });

            debugLog(`Rendered user list: ${sortedUsers.length} users`);
        }

        // Render messages
        function renderMessages(messages) {
            const messagesContainer = document.getElementById('chat-messages');
            const wasAtBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop <= messagesContainer.clientHeight + 50;

            messagesContainer.innerHTML = '';
            messages.forEach(msg => {
                const msgElement = document.createElement('div');
                msgElement.className = 'chat-message';

                const timestamp = document.createElement('span');
                timestamp.className = 'timestamp';
                timestamp.textContent = new Date(msg.timestamp).toLocaleTimeString();

                const user = document.createElement('span');
                user.className = 'user';
                user.textContent = msg.user;

                const text = document.createElement('span');
                text.className = 'text';
                text.textContent = msg.text;

                msgElement.appendChild(timestamp);
                msgElement.appendChild(user);
                msgElement.appendChild(text);

                messagesContainer.appendChild(msgElement);
            });

            debugLog(`Rendered ${messages.length} messages`);

            // Auto-scroll to bottom if user was already at bottom
            if (wasAtBottom) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            // Update active users based on recent messages
            updateActiveUsers(messages);
        }

        // Send message
        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const messageText = input.value.trim();

            if (messageText) {
                try {
                    debugLog(`Sending message: "${messageText}"`);
                    await window.bbs.fetch(`/api/applets/${appletId}/update_state/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            action: 'post_message',
                            text: messageText
                        })
                    });
                    input.value = '';
                    debugLog('Message sent successfully');
                } catch (error) {
                    debugLog(`Failed to send message: ${error.message}`);
                    console.error('AxonChat: Failed to send message', error);
                    alert('Failed to send message. Please try again.');
                }
            }
        }

        // Connect to SSE endpoint
        function connectEventSource() {
            const statusElement = document.getElementById('connection-status');

            // Close existing connection
            if (eventSource) {
                debugLog('Closing existing SSE connection');
                eventSource.close();
            }

            statusElement.textContent = 'Connecting...';
            statusElement.className = 'disconnected';

            const sseUrl = `/api/applets/${appletId}/events/`;
            debugLog(`Creating SSE connection to: ${sseUrl}`);

            // Create SSE connection
            try {
                eventSource = new EventSource(sseUrl);
                debugLog('EventSource object created, waiting for connection...');
            } catch (error) {
                debugLog(`Failed to create EventSource: ${error.message}`);
                return;
            }

            eventSource.onopen = () => {
                debugLog('SSE connection opened successfully');
                statusElement.textContent = 'Connected';
                statusElement.className = 'connected';
            };

            eventSource.onmessage = (event) => {
                debugLog(`SSE message received: ${event.data.substring(0, 100)}...`);
                try {
                    const newState = JSON.parse(event.data);
                    if (newState && newState.messages) {
                        currentMessages = newState.messages;
                        renderMessages(currentMessages);
                    } else {
                        debugLog('Received state update with no messages');
                    }
                } catch (error) {
                    debugLog(`Error parsing SSE data: ${error.message}`);
                    console.error('AxonChat: Error parsing state update', error);
                }
            };

            eventSource.onerror = (error) => {
                debugLog(`SSE connection error - ReadyState: ${eventSource.readyState}`);
                console.error('AxonChat: SSE connection error', error);
                statusElement.textContent = 'Reconnecting...';
                statusElement.className = 'disconnected';
                // Browser will automatically reconnect
            };
        }

        // Set up event listeners
        debugLog('Setting up event listeners');
        document.getElementById('chat-send').addEventListener('click', sendMessage);
        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // Render initial user list (at least shows current user)
        renderUserList();

        // Fetch initial state and connect to SSE
        try {
            debugLog(`Fetching initial state from /api/applets/${appletId}/shared_state/`);
            const initialState = await window.bbs.fetch(`/api/applets/${appletId}/shared_state/`);
            debugLog(`Initial state response: ${JSON.stringify(initialState).substring(0, 200)}`);

            if (initialState && initialState.state_data && initialState.state_data.messages) {
                currentMessages = initialState.state_data.messages;
                debugLog(`Found ${currentMessages.length} messages in initial state`);
                renderMessages(currentMessages);
            } else {
                debugLog('No messages in initial state, starting with empty chat');
            }
        } catch (error) {
            debugLog(`Could not fetch initial state: ${error.message}`);
            console.warn('AxonChat: Could not fetch initial state, starting with empty chat', error);
        }

        // Connect to SSE for real-time updates
        debugLog('Connecting to SSE stream...');
        connectEventSource();

        // Cleanup function for when applet is stopped
        window.addEventListener('beforeunload', () => {
            if (eventSource) {
                eventSource.close();
                debugLog('EventSource connection closed on unload');
            }
        });

        debugLog('AxonChat initialization complete');

    } catch (e) {
        console.error("AxonChat: Fatal error during initialization", e);
        appletContainer.innerHTML = `
            <div style="padding: 20px; color: #ffdddd; background-color: #330000; border: 1px solid #880000; font-family: monospace;">
                <h2>Chat Error</h2>
                <p>${e.message}</p>
                <pre>${e.stack}</pre>
            </div>
        `;
    }
})();
