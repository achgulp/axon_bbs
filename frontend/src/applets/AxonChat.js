// Axon BBS - A modern, anonymous, federated bulletin board system.
// Copyright (C) 2025 Achduke7
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// Full path: axon_bbs/frontend/src/applets/AxonChat.js

class AxonChat {
    constructor(bbs, appletId) {
        this.bbs = bbs;
        this.appletId = appletId;
        this.eventSource = null;
        this.state = {
            messages: [],
            users: []
        };
        this.initUI();
    }

    initUI() {
        const container = document.getElementById('applet-container');
        container.innerHTML = `
            <div id="chat-wrapper">
                <div id="chat-messages"></div>
                <div id="chat-input-area">
                    <input type="text" id="chat-input" placeholder="Type a message...">
                    <button id="chat-send">Send</button>
                </div>
            </div>
        `;

        document.getElementById('chat-send').addEventListener('click', () => this.sendMessage());
        document.getElementById('chat-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
    }

    async run() {
        // Fetch the initial state to load history immediately
        await this.fetchInitialState();
        // Start listening for real-time updates using SSE
        this.connectEventSource();
    }

    async fetchInitialState() {
        try {
            const initialState = await this.bbs.fetch(`/api/applets/${this.appletId}/state/`);
            if (initialState && initialState.messages) {
                this.state = initialState;
                this.renderMessages();
            }
        } catch (error) {
            console.error('AxonChat: Failed to fetch initial state', error);
        }
    }

    connectEventSource() {
        // Close any existing connection before starting a new one
        if (this.eventSource) {
            this.eventSource.close();
        }

        // The EventSource API handles the persistent HTTP connection
        this.eventSource = new EventSource(`/api/applets/${this.appletId}/events/`);

        // This event is fired for every message received from the server
        this.eventSource.onmessage = (event) => {
            try {
                const newState = JSON.parse(event.data);
                this.state = newState;
                this.renderMessages();
            } catch (error) {
                console.error('AxonChat: Error parsing state update', error);
            }
        };

        // This event handles connection errors, which is crucial for Tor
        this.eventSource.onerror = (error) => {
            console.error('AxonChat: EventSource failed. It will automatically attempt to reconnect.', error);
            // The browser will automatically try to reconnect after a delay.
            // No manual intervention is needed.
        };
    }

    renderMessages() {
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = ''; // Clear existing messages
        this.state.messages.forEach(msg => {
            const msgElement = document.createElement('div');
            msgElement.className = 'chat-message';
            msgElement.textContent = `[${new Date(msg.timestamp).toLocaleTimeString()}] ${msg.user}: ${msg.text}`;
            messagesContainer.appendChild(msgElement);
        });
        // Auto-scroll to the bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const messageText = input.value.trim();

        if (messageText) {
            try {
                // The update_state endpoint remains the same. The applet sends
                // its message, and the backend handles updating the state.
                // The new state will then be broadcast to all listening clients
                // via their SSE connections.
                await this.bbs.fetch(`/api/applets/${this.appletId}/update_state/`, {
                    method: 'POST',
                    body: JSON.stringify({
                        action: 'post_message',
                        text: messageText
                    }),
                });
                input.value = ''; // Clear input field on success
            } catch (error) {
                console.error('AxonChat: Failed to send message', error);
            }
        }
    }

    // This method is called by the AppletRunner if the applet is being stopped
    stop() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
            console.log('AxonChat: EventSource connection closed.');
        }
    }
}
