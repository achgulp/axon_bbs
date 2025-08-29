// Full path: frontend/src/applets/FloatUpMaze.js

// --- Start of Applet API Helper ---
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
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    const styles = `
        body { font-family: 'Arial', sans-serif; display: flex; justify-content: center; align-items: center; background-color: #1a202c; color: #e2e8f0; padding-top: 20px; overflow: hidden; }
        .game-container { background-color: #2d3748; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; width: 300px; }
        canvas { display: block; margin: 0 auto 15px auto; background-color: #e0f2fe; border: 1px solid #4a5568; max-width: 100%; height: auto; image-rendering: pixelated; }
        .controls button, .start-button { background-color: #3b82f6; color: white; border: none; padding: 10px 15px; margin: 5px; border-radius: 8px; font-size: 16px; cursor: pointer; }
        .char-select button { background-color: #4a5568; width: 48px; height: 48px; padding: 5px; display: inline-flex; justify-content: center; align-items: center; border-radius: 8px; }
        .char-select button.selected { background-color: #10b981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.5); }
        .message-area { margin-top: 10px; font-size: 18px; font-weight: bold; min-height: 25px; color: #cbd5e0; }
        .score-stats-area { display: flex; justify-content: center; font-size: 14px; margin-top: 5px; color: #a0aec0; min-height: 20px; }
        /* NEW: Debug Dialog Styles */
        #debug-dialog { position: absolute; top: 10px; left: 10px; width: 250px; height: 150px; background-color: rgba(0,0,0,0.7); border: 1px solid #4a5568; border-radius: 5px; color: #9f7aea; font-family: monospace; font-size: 10px; overflow-y: scroll; padding: 5px; z-index: 1000; }
        #debug-dialog-header { padding: 2px 5px; cursor: move; background-color: #4a5568; color: white; font-weight: bold; user-select: none; }
    `;
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);
    
    const appletRoot = document.getElementById('applet-root');
    appletRoot.innerHTML = `
        <div id="debug-dialog">
            <div id="debug-dialog-header">Debug Console</div>
        </div>
        <div class="game-container">
            <h1 class="text-2xl font-bold mb-2">FloatUp Maze</h1>
            <canvas id="gameCanvas" width="240" height="320"></canvas>
            <div id="messageArea" class="message-area">Loading...</div>
            <div class="score-stats-area"><div id="statsArea"></div></div>
            <div class="char-select my-3">
                <span class="mr-2 font-semibold align-middle">Character:</span>
                <button id="charGiraffe" data-char="giraffe" title="Giraffe"><img id="imgGiraffe" alt="Giraffe"></button>
                <button id="charElephant" data-char="elephant" title="Elephant"><img id="imgElephant" alt="Elephant"></button>
                <button id="charZebra" data-char="zebra" title="Zebra"><img id="imgZebra" alt="Zebra"></button>
            </div>
            <div class="controls mb-3">
                <button id="leftButton">← Left</button>
                <button id="rightButton">Right →</button>
            </div>
            <button id="startButton" class="start-button w-full" disabled>Start Game</button>
        </div>
    `;

    // --- NEW: Debug Dialog Logic ---
    const debugDialog = document.getElementById('debug-dialog');
    const debugHeader = document.getElementById('debug-dialog-header');
    let isDragging = false;
    let offsetX, offsetY;

    function debugLog(message) {
        const logEntry = document.createElement('div');
        logEntry.textContent = `> ${message}`;
        debugDialog.appendChild(logEntry);
        debugDialog.scrollTop = debugDialog.scrollHeight; // Auto-scroll to bottom
    }

    debugHeader.addEventListener('mousedown', (e) => {
        isDragging = true;
        offsetX = e.clientX - debugDialog.offsetLeft;
        offsetY = e.clientY - debugDialog.offsetTop;
        debugDialog.style.opacity = '0.7';
    });

    document.addEventListener('mousemove', (e) => {
        if (isDragging) {
            debugDialog.style.left = `${e.clientX - offsetX}px`;
            debugDialog.style.top = `${e.clientY - offsetY}px`;
        }
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        debugDialog.style.opacity = '1';
    });

    // --- Game Logic ---
    const canvas = document.getElementById('gameCanvas');
    const ctx = canvas.getContext('2d');
    const messageArea = document.getElementById('messageArea');
    const statsArea = document.getElementById('statsArea');
    const startButton = document.getElementById('startButton');
    
    let stats = { wins: 0, mineHits: 0, abductions: 0, spaceLosses: 0 };
    
    function updateStatsDisplay() {
        statsArea.innerHTML = `🏆: ${stats.wins} | 💥: ${stats.mineHits} | 👽: ${stats.abductions} | 🌌: ${stats.spaceLosses}`;
    }

    async function handleWin() {
        // ... (rest of function)
        stats.wins++;
        debugLog(`Win! New score: ${stats.wins}`);
        await bbs.saveData(stats);
        resetGameAfterDelay();
    }

    async function handleLose(reason = "Try Again!") {
        // ... (rest of function)
        if (reason === "Hit a mine!") stats.mineHits++;
        else if (reason === "Abducted!") stats.abductions++;
        else if (reason === "Floated into space!") stats.spaceLosses++;
        debugLog(`Lose: ${reason}`);
        await bbs.saveData(stats);
        resetGameAfterDelay();
    }
    
    // --- (All other game functions and variables are unchanged) ---
    // You can now add `debugLog()` anywhere in the game logic to watch variables.
    // Example: In the startGame() function, you could add:
    // debugLog(`Starting game with char: ${selectedCharacter}`);
    
    // --- Initial Setup ---
    debugLog("Applet initializing...");
    try {
        const [user, savedData] = await Promise.all([bbs.getUserInfo(), bbs.getData()]);
        debugLog(`User info received for: ${user.username}`);
        const container = document.querySelector('.game-container');
        const welcomeArea = document.createElement('p');
        welcomeArea.textContent = `Welcome, ${user.nickname || user.username}!`;
        welcomeArea.className = 'text-sm text-gray-400 mt-2';
        container.appendChild(welcomeArea);

        if (savedData && Object.keys(savedData).length > 0) {
            stats = savedData;
            debugLog("Loaded saved stats from BitSync.");
        } else {
            debugLog("No saved stats found.");
        }
        updateStatsDisplay();
        
        loadAssets(); // This now happens AFTER user info is loaded

    } catch (e) {
        messageArea.textContent = "Error initializing with BBS!";
        debugLog(`Error: ${e.message}`);
    }

    // (The rest of your game logic: bitmaps, event listeners, etc. should be pasted here)

})();
