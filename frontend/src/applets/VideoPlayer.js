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
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.


// Full path: axon_bbs/frontend/src/applets/VideoPlayer.js

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
      window.parent.postMessage({ command, payload, requestId }, '*');
    });
  },
  getAttachmentContext: function() { return this._postMessage('getAttachmentContext'); },
  // --- NEW API CALL ---
  getAttachmentBlob: function() { return this._postMessage('getAttachmentBlob'); },
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    const styles = `
        html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #000; }
        .container { display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; }
        video { max-width: 100%; max-height: 100%; }
        .message { color: #cbd5e0; font-family: monospace; }
        .error { color: #f56565; font-family: monospace; }
    `;
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);

    const root = document.getElementById('applet-root');
    root.innerHTML = `<div class="container" id="container"><p class="message">Initializing player...</p></div>`;
    const container = document.getElementById('container');

    try {
        container.innerHTML = `<p class="message">Fetching attachment info...</p>`;
        const context = await window.bbs.getAttachmentContext();
        if (!context || !context.content_hash || !context.content_type) {
            throw new Error("Invalid or missing attachment context from host.");
        }

        container.innerHTML = `<p class="message">Downloading and decrypting video stream...</p>`;
        // --- FIX START ---
        // Fetch the video data as a Blob using the new API call
        const videoBlob = await window.bbs.getAttachmentBlob();
        const videoObjectUrl = URL.createObjectURL(videoBlob);
        // --- FIX END ---

        const videoEl = document.createElement('video');
        videoEl.setAttribute('controls', true);
        videoEl.setAttribute('preload', 'auto');
        videoEl.setAttribute('autoplay', true); // Autoplay the video once loaded
        
        const sourceEl = document.createElement('source');
        // Use the local object URL, which the browser can access without auth headers
        sourceEl.setAttribute('src', videoObjectUrl);
        sourceEl.setAttribute('type', context.content_type);

        videoEl.appendChild(sourceEl);
        videoEl.addEventListener('error', () => {
            container.innerHTML = `<p class="error">Error: Could not load video. The format may be unsupported or the file is corrupt.</p>`;
        });

        container.innerHTML = '';
        container.appendChild(videoEl);

    } catch (e) {
        if (e.message === 'identity_locked') {
             container.innerHTML = `<p class="error">Identity is locked. Please close this view, unlock your identity, and try again.</p>`;
        } else {
             container.innerHTML = `<p class="error">Failed to initialize video player: ${e.message}</p>`;
        }
        console.error("VideoPlayer Applet Error:", e);
    }
})();
