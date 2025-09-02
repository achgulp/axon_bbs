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


// Axon BBS Applet Template
// Version: 1.0

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
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData');
  },
  saveData: function(newData) { return this._postMessage('saveData', newData); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    // 1. SETUP: Define styles, create HTML structure, and declare variables.
    
    // --- STYLES ---
    const styles = `
        /* Add all your CSS rules here. Make it responsive! */
        body { font-family: sans-serif; background-color: #1a202c; color: #e2e8f0; display: flex; justify-content: center; align-items: center; }
        .applet-container { background-color: #2d3748; padding: 20px; border-radius: 10px; text-align: center; }
        #debug-dialog { display: none; /* Hidden by default */ position: absolute; top: 10px; left: 10px; width: 250px; height: 150px; background-color: rgba(0,0,0,0.7); border: 1px solid #4a5568; border-radius: 5px; color: #fc8181; font-family: monospace; font-size: 10px; overflow-y: scroll; padding: 5px; z-index: 1000; }
        #debug-dialog-header { padding: 2px 5px; cursor: move; background-color: #4a5568; color: white; font-weight: bold; user-select: none; }
    `;
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);
    
    // --- HTML STRUCTURE ---
    document.getElementById('applet-root').innerHTML = `
        <div id="debug-dialog"><div id="debug-dialog-header">Debug Console</div></div>
        <div class="applet-container">
            <h1 id="welcome-message" class="text-2xl font-bold mb-2">My New Applet</h1>
            <p id="data-display">Loading saved data...</p>
            <button id="action-button" style="padding: 10px; margin-top: 20px;">Perform Action</button>
        </div>
    `;
    
    // --- VARIABLES & DOM REFERENCES ---
    const debugDialog = document.getElementById('debug-dialog');
    const welcomeMessage = document.getElementById('welcome-message');
    const dataDisplay = document.getElementById('data-display');
    const actionButton = document.getElementById('action-button');
    let userProfile = null;
    let appletData = { clicks: 0 }; // Default data structure

    // --- FUNCTIONS ---
    function debugLog(message) {
        if (window.BBS_DEBUG_MODE !== true) return;
        const logEntry = document.createElement('div');
        const text = `> ${message}`;
        console.log(text);
        logEntry.textContent = text;
        debugDialog.appendChild(logEntry);
        debugDialog.scrollTop = debugDialog.scrollHeight;
    }

    function updateUI() {
        if (userProfile) {
            welcomeMessage.textContent = `Welcome, ${userProfile.nickname || userProfile.username}!`;
        }
        dataDisplay.textContent = `You have clicked the button ${appletData.clicks} time(s).`;
    }

    async function handleAction() {
        appletData.clicks = (appletData.clicks || 0) + 1;
        debugLog(`Action performed. Click count is now ${appletData.clicks}.`);
        
        try {
            await bbs.saveData(appletData);
            debugLog("Data saved successfully.");
        } catch (e) {
            debugLog(`Error saving data: ${e.message}`);
        }
        
        updateUI();
    }

    // 2. RUNTIME: Initialize the applet.
    try {
        if (window.BBS_DEBUG_MODE === true) {
            debugDialog.style.display = 'block';
        }
        debugLog("Applet initializing...");

        // Load user info and saved data in parallel
        const [user, savedData] = await Promise.all([bbs.getUserInfo(), bbs.getData()]);
        
        userProfile = user;
        debugLog(`User info received for: ${userProfile.username}`);

        if (savedData && typeof savedData === 'object') {
            appletData = { ...appletData, ...savedData }; // Merge saved data with default structure
            debugLog("Loaded saved data from BitSync.");
        } else {
            debugLog("No saved data found. Using defaults.");
        }

        // Add event listeners
        actionButton.addEventListener('click', handleAction);

        // Initial UI update
        updateUI();

    } catch (e) {
        const root = document.getElementById('applet-root');
        root.innerHTML = `<p style="color: red;">Error initializing with BBS: ${e.message}</p>`;
        debugLog(`FATAL ERROR: ${e.message}`);
    }
})();

