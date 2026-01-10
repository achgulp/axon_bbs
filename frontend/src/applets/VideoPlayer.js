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

// Added for test.
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
  getAttachmentBlob: function() { return this._postMessage('getAttachmentBlob'); },
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
// --- FIX START ---
// Reverted to a self-executing async function. The AppletRunner already ensures
// the DOM is ready, so an extra listener here prevents the code from ever running.
(async function() {
    const styles = `
        html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: #000; }
        .container { display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; }
        video { max-width: 100%; max-height: 100%; }
        .message { color: #cbd5e0; font-family: monospace; }
        .error { color: #f56565; font-family: monospace; padding: 20px; text-align: center; }
        #debug-dialog { display: none; position: absolute; bottom: 10px; left: 10px; width: 350px; height: 250px; background-color: rgba(0,0,0,0.8); border: 1px solid #4a5568; border-radius: 5px; color: #9AE6B4; font-family: monospace; font-size: 12px; overflow-y: scroll; padding-top: 25px; z-index: 1000; }
        #debug-header { position: absolute; top: 0; left: 0; right: 0; background-color: #4a5568; color: white; font-weight: bold; padding: 3px; cursor: move; user-select: none; }
    `;
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);

    const root = document.getElementById('applet-root');
    root.innerHTML = `
        <div id="debug-dialog"><div id="debug-header">DEBUG CONSOLE</div></div>
        <div class="container" id="container"><p class="message">Loading player...</p></div>
    `;
    const container = document.getElementById('container');
    const debugDialog = document.getElementById('debug-dialog');

    function debugLog(message) {
        if (window.BBS_DEBUG_MODE !== true) return;
        debugDialog.style.display = 'block';
        const logEntry = document.createElement('div');
        logEntry.textContent = `> ${message}`;
        debugDialog.appendChild(logEntry);
        debugDialog.scrollTop = debugDialog.scrollHeight;
    }
    
    function displayError(e) {
        let errorMessage;
        if (e.message === 'identity_locked') {
            errorMessage = `Identity is locked. Please close this view, unlock your identity, and try again.`;
        } else {
            errorMessage = `Failed to initialize video player: ${e.message}`;
        }
        container.innerHTML = `<p class="error">${errorMessage}</p>`;
        debugLog(`FATAL ERROR: ${e.stack}`);
        console.error("VideoPlayer Applet Error:", e);
    }

    try {
        debugLog("Applet initializing...");
        
        container.innerHTML = `<p class="message">Fetching attachment info...</p>`;
        debugLog("Checkpoint 1: Requesting attachment context...");
        const context = await window.bbs.getAttachmentContext();
        debugLog("Checkpoint 2: Attachment context received.");

        if (!context || !context.content_hash || !context.content_type) {
            throw new Error("Invalid or missing attachment context from host.");
        }
        debugLog(`Context OK: hash=${context.content_hash.substring(0,10)}..., type=${context.content_type}`);

        container.innerHTML = `<p class="message">Downloading and decrypting video stream...</p>`;
        debugLog("Checkpoint 3: Requesting attachment blob...");
        const videoBlob = await window.bbs.getAttachmentBlob();
        debugLog(`Checkpoint 4: Blob received. Size: ${videoBlob.size} bytes.`);

        const videoObjectUrl = URL.createObjectURL(videoBlob);
        debugLog("Checkpoint 5: Created object URL for blob.");

        // --- FINAL FIX START ---
        // Display a play button to require user interaction, satisfying modern browser security.
        const playButton = document.createElement('button');
        playButton.textContent = '▶ Play Video';
        playButton.className = 'play-button'; // Add a class for styling
        container.innerHTML = '';
        container.appendChild(playButton);

        // Add styles for the button
        const buttonStyles = `
            .play-button {
                background-color: #4a5568; border: none; color: white; padding: 15px 32px;
                text-align: center; font-size: 16px; cursor: pointer; border-radius: 5px;
            }
            .play-button:hover { background-color: #718096; }
        `;
        const buttonStyleSheet = document.createElement("style");
        buttonStyleSheet.innerText = buttonStyles;
        document.head.appendChild(buttonStyleSheet);

        playButton.addEventListener('click', () => {
            debugLog("Play button clicked. Creating video element...");
            const videoEl = document.createElement('video');
            videoEl.setAttribute('controls', true);
            videoEl.setAttribute('preload', 'auto');
            
            const sourceEl = document.createElement('source');
            sourceEl.setAttribute('src', videoObjectUrl);
            sourceEl.setAttribute('type', context.content_type);

            videoEl.appendChild(sourceEl);
            videoEl.addEventListener('error', (err) => {
                displayError(new Error("Browser could not play video. The format may be unsupported, the file may be corrupt, or there was a streaming error."));
            });

            container.innerHTML = '';
            container.appendChild(videoEl);
            debugLog("Checkpoint 6: Video player created and rendered.");

            debugLog("Checkpoint 7: Attempting to programmatically play video...");
            const playPromise = videoEl.play();
            if (playPromise !== undefined) {
                playPromise.then(_ => {
                    debugLog("Playback started successfully.");
                }).catch(error => {
                    debugLog(`Playback failed: ${error}`);
                    displayError(new Error(`Browser prevented video from playing: ${error}`));
                });
            }
        }, { once: true }); // The listener runs only once
        // --- FINAL FIX END ---

    } catch (e) {
        displayError(e);
    }
})();
// --- FIX END ---
