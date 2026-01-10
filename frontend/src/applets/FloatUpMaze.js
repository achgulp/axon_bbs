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


// Full path: axon_bbs/frontend/src/applets/FloatUpMaze.js

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
  // --- Standard API ---
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); },

  // --- NEW: Event Bus API ---
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); },
  postEvent: function(eventData) { return this._postMessage('postEvent', eventData); },
  readEvents: function() { return this._postMessage('readEvents'); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    // 1. SETUP: Inject CSS, create HTML, and define all variables and functions first.
    const styles = `
        body { font-family: 'Arial', sans-serif; display: flex; justify-content: center; align-items: center; background-color: #1a202c; color: #e2e8f0; padding-top: 20px; overflow: hidden; }
        .game-container { background-color: #2d3748; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); text-align: center; width: 300px; }
        
        #gameCanvas { 
            display: block; 
            margin: 0 auto 15px auto; 
            background-color: #e0f2fe; 
            border: 1px solid #4a5568; 
            max-width: 100%; 
            height: auto; 
            image-rendering: pixelated; 
            image-rendering: -moz-crisp-edges; 
            image-rendering: crisp-edges;
        }

        .controls button, .start-button { background-color: #3b82f6; color: white; border: none; padding: 10px 15px; margin: 5px; border-radius: 8px; font-size: 16px; cursor: pointer; }
        .char-select button { background-color: #4a5568;
        width: 48px; height: 48px; padding: 0;
        display: inline-flex; justify-content: center; align-items: center; border-radius: 8px; border: none;
        }
        .char-select button.selected { background-color: #10b981; box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.5); }
        .message-area { margin-top: 10px; font-size: 18px; font-weight: bold; min-height: 25px; color: #cbd5e0; }
        .score-stats-area { display: flex; justify-content: center; font-size: 14px; margin-top: 5px; color: #a0aec0; min-height: 20px; }
        #debug-dialog { position: absolute; top: 10px; left: 10px; width: 250px; height: 150px; background-color: rgba(0,0,0,0.7); border: 1px solid #4a5568; border-radius: 5px; color: #fc8181; font-family: monospace; font-size: 10px; overflow-y: scroll; padding: 5px; z-index: 1000; }
        #debug-dialog-header { padding: 2px 5px; cursor: move; background-color: #4a5568; color: white; font-weight: bold; user-select: none; }
    `;
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);
    document.getElementById('applet-root').innerHTML = `
        <div id="debug-dialog"><div id="debug-dialog-header">Debug Console</div></div>
        <div class="game-container">
            <h1 class="text-2xl font-bold mb-2">FloatUp Maze</h1>
            <canvas id="gameCanvas" width="240" height="320"></canvas>
            <div id="messageArea" class="message-area">Loading...</div>
            <div class="score-stats-area"><div id="statsArea"></div></div>
            <div class="char-select my-3">
                <span class="mr-2 font-semibold align-middle">Character:</span>
                <button id="charGiraffe" data-char="giraffe" title="Giraffe"><canvas width="48" height="48"></canvas></button>
                <button id="charElephant" data-char="elephant" title="Elephant"><canvas width="48" height="48"></canvas></button>
                <button id="charZebra" data-char="zebra" title="Zebra"><canvas width="48" height="48"></canvas></button>
            </div>
            <div class="controls mb-3">
                <button id="leftButton">← Left</button>
                <button id="rightButton">Right →</button>
            </div>
            <button id="startButton" class="start-button w-full" disabled>Start Game</button>
        </div>
    `;
    const debugDialog = document.getElementById('debug-dialog');
    const debugHeader = document.getElementById('debug-dialog-header');
    let isDragging = false, offsetX, offsetY;
    debugHeader.addEventListener('mousedown', (e) => { isDragging = true; offsetX = e.clientX - debugDialog.offsetLeft; offsetY = e.clientY - debugDialog.offsetTop; });
    document.addEventListener('mousemove', (e) => { if (isDragging) { debugDialog.style.left = `${e.clientX - offsetX}px`; debugDialog.style.top = `${e.clientY - offsetY}px`; } });
    document.addEventListener('mouseup', () => { isDragging = false; });

    // UPDATED: The debugLog function now respects the global debug flag
    function debugLog(message) {
        if (window.BBS_DEBUG_MODE !== true) return;
        const logEntry = document.createElement('div');
        const text = `> ${message}`;
        console.log(text);
        logEntry.textContent = text;
        debugDialog.appendChild(logEntry);
        debugDialog.scrollTop = debugDialog.scrollHeight;
    }

    try {
        // UPDATED: Hide the debug console if debug mode is off
        if (window.BBS_DEBUG_MODE !== true) {
            debugDialog.style.display = 'none';
        }

        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = false;
        const messageArea = document.getElementById('messageArea');
        const statsArea = document.getElementById('statsArea');
        const startButton = document.getElementById('startButton');
        const leftButton = document.getElementById('leftButton');
        const rightButton = document.getElementById('rightButton');
        const charButtons = document.querySelectorAll('.char-select button');
        let stats = { wins: 0, losses: 0, deaths: 0, abductions: 0, spaceLosses: 0, score: 0 };
        let player, trophy, mines = [], explosionParticles = [], safePathSegments = [];
        let isGameRunning = false, isGameOver = false, isExploding = false, explosionTimer = 0;
        let selectedCharacter = null;
        let moveLeft = false, moveRight = false;
        let animationFrameId = null;
        let approachingTopOutcome = null;
        let saucer = { active: false, x: 0, y: -30, width: 40, height: 20, speed: 2, state: 'idle', beamActive: false, pullSpeed: 1.5 };
        const T = null, K = '#000000', W = '#FFFFFF', G = '#808080', LG = '#D3D3D3', Y = '#FFD700', BR = '#A0522D', DG = '#333333', OR = '#FFA500', FY = '#FFFF00', SC = '#C0C0C0', BC = 'rgba(173, 216, 230, 0.5)', GC = '#228B22', LGC = '#90EE90', TRUNK_C = '#8B4513';
        const giraffeBitmap = [ [T, T, T, T, T, Y, Y, T, T, T, T, T, T, T, T, T],[T, T, T, T, Y, Y, Y, Y, T, T, T, T, T, T, T, T],[T, T, T, T, Y, BR, Y, Y, T, T, T, T, T, T, T, T],[T, T, T, T, T, Y, Y, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, Y, Y, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, Y, Y, T, T, T, T, T, T, T, T, T],[T, T, T, T, Y, Y, Y, Y, T, T, T, T, T, T, T, T],[T, T, T, Y, Y, BR, Y, Y, Y, T, T, T, T, T, T, T],[T, T, T, Y, Y, Y, Y, Y, Y, T, T, T, T, T, T, T],[T, T, T, Y, Y, T, T, Y, Y, T, T, T, T, T, T, T],[T, T, T, Y, Y, T, T, Y, Y, T, T, T, T, T, T, T],[T, T, T, Y, Y, T, T, Y, Y, T, T, T, T, T, T, T],[T, T, T, Y, Y, T, T, Y, Y, T, T, T, T, T, T, T],[T, T, T, BR, BR, T, T, BR, BR, T, T, T, T, T, T, T],[T, T, T, BR, BR, T, T, BR, BR, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T]];
        const elephantBitmap = [ [T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, G, G, G, G, G, G, G, T, T, T, T, T],[T, T, T, G, G, G, G, G, G, G, G, G, T, T, T, T],[T, T, G, G, LG, G, G, G, LG, G, G, G, G, T, T, T],[T, T, G, G, G, G, G, G, G, G, G, G, G, T, T, T],[T, G, G, G, G, G, G, G, G, G, G, G, G, G, T, T],[T, G, G, G, G, G, G, G, G, G, G, G, G, G, T, T],[T, G, G, G, G, T, T, T, T, T, G, G, G, G, T, T],[T, T, G, G, T, T, T, T, T, T, T, G, G, T, T, T],[T, T, G, G, T, T, G, G, T, T, T, G, G, T, T, T],[T, T, G, G, T, G, G, G, G, T, G, G, T, T, T, T],[T, T, G, G, T, G, G, G, G, T, G, G, T, T, T, T],[T, T, G, G, T, T, G, G, T, T, G, G, T, T, T, T],[T, T, G, G, T, T, G, G, T, T, G, G, T, T, T, T],[T, T, T, LG, LG, T, T, LG, LG, T, T, LG, LG, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T]];
        const zebraBitmap = [ [T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, W, K, W, K, T, T, T, T, T, T, T],[T, T, T, T, W, K, W, K, W, K, T, T, T, T, T, T],[T, T, T, K, W, K, W, K, W, K, W, T, T, T, T, T],[T, T, T, W, K, W, K, W, K, W, K, T, T, T, T, T],[T, T, T, K, W, K, W, K, W, K, W, T, T, T, T, T],[T, T, T, W, K, W, K, K, W, K, W, K, T, T, T, T, T],[T, T, T, K, W, K, W, K, W, K, W, T, T, T, T, T],[T, T, T, W, K, W, K, W, K, W, K, T, T, T, T, T],[T, T, T, K, W, K, W, K, W, K, W, T, T, T, T, T],[T, T, T, W, K, W, T, T, K, W, T, T, T, T, T, T],[T, T, T, K, K, T, T, T, T, K, T, T, T, T, T, T],[T, T, T, W, W, T, T, T, T, W, T, T, T, T, T, T],[T, T, T, K, K, T, T, T, T, K, T, T, T, T, T, T],[T, T, T, W, W, T, T, T, T, W, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T]];
        const simpleBombBitmap = [ [T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, BR, BR, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, BR, OR, FY, BR, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, BR, FY, OR, BR, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, DG, DG, DG, DG, DG, DG, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, DG, DG, DG, DG, DG, DG, DG, DG, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, DG, DG, K, K, K, K, K, K, DG, DG, T, T, T, T, T, T, T],[T, T, T, T, T, T, DG, DG, K, K, W, K, K, W, K, K, DG, DG, T, T, T, T, T, T],[T, T, T, T, T, T, DG, K, K, K, K, K, K, K, K, K, K, DG, T, T, T, T, T, T],[T, T, T, T, T, T, DG, K, K, K, K, K, K, K, K, K, K, DG, T, T, T, T, T, T],[T, T, T, T, T, T, DG, K, K, K, K, K, K, K, K, K, K, DG, T, T, T, T, T, T],[T, T, T, T, T, T, DG, DG, K, K, K, K, K, K, K, K, DG, DG, T, T, T, T, T, T],[T, T, T, T, T, T, T, DG, DG, K, K, K, K, K, K, DG, DG, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, DG, DG, DG, DG, DG, DG, DG, DG, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, DG, DG, DG, DG, DG, DG, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T],[T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T, T]];
        const characterBitmaps = { giraffe: giraffeBitmap, elephant: elephantBitmap, zebra: zebraBitmap };
        let sounds = {}, audioInitialized = false;
        function drawBitmap(ctx, bitmap, x, y, scale = 1) {
            const height = bitmap.length;
            if (height === 0) return;
            const width = bitmap[0].length;
            if (width === 0) return;
            for (let row = 0; row < height; row++) {
                for (let col = 0; col < width; col++) {
                    if (bitmap[row][col]) {
                        ctx.fillStyle = bitmap[row][col];
                        ctx.fillRect(x + (col * scale), y + (row * scale), scale, scale);
                    }
                }
            }
        }
        
        function updateStatsDisplay() { 
            statsArea.innerHTML = `🏆: ${stats.wins} | ☠️: ${stats.deaths} | 👽: ${stats.abductions} | 🌌: ${stats.spaceLosses} | 📉: ${stats.losses} | <b>Score: ${stats.score || 0}</b>`;
        }
        
        async function handleWin() { 
            if (isGameOver || isExploding) return;
            isGameOver = true; isGameRunning = false; playSound('win'); 
            stats.wins = (stats.wins || 0) + 1;
            stats.score = (stats.score || 0) + 1000;
            messageArea.textContent = "You Win! +1000 points!"; 
            await bbs.saveData(stats); 
            debugLog(`Win! Stats saved.`); 
            resetGameAfterDelay();
        }

        async function handleLose(reason = "Try Again!") { 
            if (isGameOver) return;
            isGameOver = true; isGameRunning = false; 
            
            stats.losses = (stats.losses || 0) + 1;
            if (reason === "Hit a mine!") {
                stats.deaths = (stats.deaths || 0) + 1;
                stats.score = (stats.score || 0) - 50;
            } else if (reason === "Abducted!") {
                stats.abductions = (stats.abductions || 0) + 1;
            } else if (reason === "Floated into space!") {
                stats.spaceLosses = (stats.spaceLosses || 0) + 1;
            }

            playSound('lose'); 
            messageArea.textContent = `Game Over! ${reason}`; 
            await bbs.saveData(stats);
            debugLog(`Lose: ${reason}. Stats saved.`);
            resetGameAfterDelay(); 
        }
        
        function setupUI() {
            debugLog("Setting up UI...");
            const charCanvases = {
                giraffe: document.querySelector('#charGiraffe canvas'),
                elephant: document.querySelector('#charElephant canvas'),
                zebra: document.querySelector('#charZebra canvas')
            };
            for (const charName in charCanvases) {
                const btnCanvas = charCanvases[charName];
                const btnCtx = btnCanvas.getContext('2d');
                btnCtx.imageSmoothingEnabled = false;
                btnCtx.clearRect(0, 0, btnCanvas.width, btnCanvas.height); 
                const bitmap = characterBitmaps[charName];
                const scale = 2;
                const bitmapWidth = bitmap[0].length * scale;
                const bitmapHeight = bitmap.length * scale;
                const x = (btnCanvas.width - bitmapWidth) / 2;
                const y = (btnCanvas.height - bitmapHeight) / 2 + 12;
                drawBitmap(btnCtx, bitmap, x, y, scale);
            }
            
            messageArea.textContent = "Select character & Start!";
            startButton.disabled = false;
        }

        function initializeAudio() { if (audioInitialized) return Promise.resolve();
        return new Promise((resolve, reject) => { if (typeof Tone === 'undefined') { const script = document.createElement('script'); script.src = "https://cdnjs.cloudflare.com/ajax/libs/tone/14.8.49/Tone.js"; script.onload = () => { setupTones(); resolve(); }; script.onerror = reject; document.head.appendChild(script); } else { setupTones(); resolve(); } });
        }
        function setupTones() { sounds.collision = new Tone.Synth({ oscillator: { type: "square" }, envelope: { attack: 0.01, decay: 0.1, sustain: 0, release: 0.1 } }).toDestination();
        sounds.win = new Tone.Synth({ oscillator: { type: "triangle" }, envelope: { attack: 0.01, decay: 0.2, sustain: 0.1, release: 0.2 } }).toDestination();
        sounds.lose = new Tone.Synth({ oscillator: { type: "sawtooth" }, envelope: { attack: 0.01, decay: 0.3, sustain: 0, release: 0.2 } }).toDestination();
        sounds.explosion = new Tone.NoiseSynth({ noise: { type: 'white' }, envelope: { attack: 0.005, decay: 0.1, sustain: 0, release: 0.1 } }).toDestination();
        sounds.beam = new Tone.AMOscillator({frequency: 100, type: "sine", modulationType: "sine", harmonicity: 1.01}).toDestination(); sounds.beam.volume.value = -15; audioInitialized = true;
        }
        function playSound(soundName, action = 'play') { if (!audioInitialized || !sounds[soundName]) return;
        try { if (Tone.context.state !== 'running') { Tone.context.resume(); } if (soundName === 'beam') { if (action === 'start' && sounds.beam.state !== 'started') { sounds.beam.start();
        } else if (action === 'stop' && sounds.beam.state === 'started') { sounds.beam.stop();
        } } else { if (soundName === 'collision') sounds.collision.triggerAttackRelease("C3", "8n"); if (soundName === 'win') sounds.win.triggerAttackRelease("C5", "4n");
        if (soundName === 'lose') sounds.lose.triggerAttackRelease("A2", "4n"); if (soundName === 'explosion') sounds.explosion.triggerAttackRelease();
        } } catch (e) { /* silent fail */ } }
        function defineTrophy() { trophy = { x: Math.random() * (canvas.width - 20), y: Math.random() * 40 + 80, width: 20, height: 30 };
        }
        function generateSafePath() { safePathSegments = [];
        let currentX = canvas.width / 2 - 20; const segHeight = canvas.height / 12;
        for (let i = 0; i < 12; i++) { const segY = canvas.height - (i + 1) * segHeight;
        let nextX = currentX + (Math.random() - 0.5) * 80; nextX = Math.max(0, Math.min(canvas.width - 40, nextX));
        safePathSegments.push({ x: nextX, y: segY, width: 40, height: segHeight }); currentX = nextX;
        } }
        function isPositionValid(x, y, w, h) { const rect = { x, y, width: w, height: h };
        if (x < 2 || x + w > canvas.width - 2 || y < 40 || y + h > canvas.height - 40) return false;
        if (trophy && checkCollision(rect, trophy)) return false; if (checkCollision(rect, { x: 0, y: canvas.height - 42, width: canvas.width, height: 42 })) return false;
        for (const mine of mines) { if (checkCollision(rect, mine)) return false;
        } for (const seg of safePathSegments) { if (checkCollision(rect, seg)) return false; } return true;
        }
        function placeMines() { mines = [];
        for (let i = 0; i < 5000 && mines.length < 15; i++) { const x = Math.random()*(canvas.width-24);
        const y = Math.random()*(canvas.height-24); if(isPositionValid(x, y, 24, 24)) mines.push({x,y,width:24,height:24});}}
        function initializePlayer() { if (!selectedCharacter) return;
        player = { x: canvas.width / 2 - 8, y: canvas.height - 21, width: 16, height: 16, bitmap: characterBitmaps[selectedCharacter] };
        }
        function clearCanvas() { ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        function drawTrophy() { if(trophy) { ctx.fillStyle = TRUNK_C;
        ctx.fillRect(trophy.x + 7, trophy.y + 18, 6, 12); ctx.fillStyle = GC; ctx.beginPath();
        ctx.arc(trophy.x + 10, trophy.y + 10, 10, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = LGC; ctx.beginPath();
        ctx.arc(trophy.x + 8, trophy.y + 8, 6, 0, Math.PI * 2); ctx.fill();
        } }
        function drawMines() { mines.forEach(m => drawBitmap(ctx, simpleBombBitmap, m.x, m.y));
        }
        function drawPlayer() { if (player && !isExploding && saucer.state !== 'beaming') drawBitmap(ctx, player.bitmap, player.x, player.y);
        }
        function drawExplosion() { explosionParticles.forEach(p => { ctx.fillStyle = p.color; ctx.fillRect(p.x - p.size/2, p.y - p.size/2, p.size, p.size); });
        }
        function drawSaucer() { if (!saucer.active) return; ctx.fillStyle = SC; ctx.beginPath();
        ctx.ellipse(saucer.x + 20, saucer.y + 10, 20, 10, 0, 0, Math.PI * 2); ctx.fill(); ctx.fillStyle = LG; ctx.beginPath();
        ctx.ellipse(saucer.x + 20, saucer.y + 5, 10, 5, 0, 0, Math.PI * 2); ctx.fill();
        }
        function drawTractorBeam() { if (!saucer.beamActive || !player) return;
        const pX = player.x + 8, pY = player.y + 8; ctx.beginPath(); ctx.moveTo(saucer.x + 6, saucer.y + 20);
        ctx.lineTo(pX - 12, pY); ctx.lineTo(pX + 12, pY); ctx.lineTo(saucer.x + 34, saucer.y + 20); ctx.closePath(); ctx.fillStyle = BC; ctx.fill();
        }
        function checkCollision(r1, r2) { if(!r1 || !r2) return false;
        return r1.x < r2.x + r2.width && r1.x + r1.width > r2.x && r1.y < r2.y + r2.height && r1.y + r1.height > r2.y;
        }
        
        function updatePlayerPosition() {
            if (!player || isGameOver || isExploding) return;
            if (trophy && checkCollision(player, trophy) && saucer.state !== 'beaming') return handleWin();
            if (saucer.state === 'beaming') {
                const dX = saucer.x + 20 - (player.x + 8), dY = saucer.y - (player.y + 8);
                const dist = Math.sqrt(dX*dX + dY*dY);
                if (dist < 16) {
                    playSound('beam', 'stop');
                    player = null;
                    saucer.active = false;
                    saucer.beamActive = false;
                    saucer.state = 'idle';
                    return handleLose("Abducted!");
                }
                player.x += (dX / dist) * 1.5;
                player.y += (dY / dist) * 1.5;
                return;
            }

            let nX = player.x;
            if (moveLeft) nX -= 1.5;
            if (moveRight) nX += 1.5;
            if (nX < 0 || nX + 16 > canvas.width) playSound('collision');
            player.x = Math.max(0, Math.min(canvas.width - 16, nX));
            const nY = player.y - 1.0;
            const triggerY = canvas.height / 2;
            if (nY < triggerY && !saucer.active && approachingTopOutcome === null) {
                if (Math.random() < 0.15) {
                    approachingTopOutcome = 'saucer';
                    saucer.active = true;
                    saucer.state = 'entering';
                    saucer.y = -20;
                    saucer.x = Math.max(0, Math.min(canvas.width-40, player.x-12));
                    saucer.targetY = triggerY - 30;
                } else {
                    approachingTopOutcome = 'space';
                }
            }

            player.y = nY;
            if (player.y + 16 <= 0) return handleLose("Floated into space!");
            if (saucer.state !== 'beaming') {
                for (const m of mines) {
                    if (checkCollision(player, m)) return triggerExplosion(player.x + 8, player.y + 8);
                }
            }
        }
        function updateSaucer() { if (!saucer.active || isExploding || isGameOver) return;
        if (saucer.state === 'entering' && saucer.y < saucer.targetY) { saucer.y += 2; if (saucer.y >= saucer.targetY) { saucer.y=saucer.targetY; saucer.state='beaming'; saucer.beamActive=true;
        playSound('beam','start');}}}
        function updateExplosion() { if (!isExploding) return;
        explosionParticles.forEach((p, i) => { p.x += p.dx; p.y += p.dy; p.life--; if(p.life <= 0) explosionParticles.splice(i,1);}); explosionTimer--;
        if (explosionTimer <= 0 && explosionParticles.length === 0) { isExploding = false; handleLose("Hit a mine!");
        } }
        function triggerExplosion(x,y) { if (isExploding||isGameOver||saucer.state === 'beaming') return; isExploding=true; isGameRunning=false; playSound('explosion');
        explosionTimer=60; explosionParticles=[]; for(let i=0; i<30; i++){const a=(Math.PI*2/30)*i, s=Math.random()*3+1; explosionParticles.push({x,y,dx:Math.cos(a)*s,dy:Math.sin(a)*s,size:Math.random()*3+1,color:`hsl(${Math.random()*60},100%,50%)`,life:Math.random()*30+20});}}
        function gameLoop() { clearCanvas();
        updateSaucer(); if (isExploding) { drawTrophy(); drawMines(); if(saucer.active) drawSaucer(); updateExplosion(); drawExplosion(); } else if (!isGameOver) { drawTrophy(); drawMines(); if (isGameRunning) updatePlayerPosition();
        drawPlayer(); if(saucer.active) drawSaucer(); if(saucer.beamActive) drawTractorBeam(); } else { drawTrophy(); drawMines(); if(saucer.active) drawSaucer(); } animationFrameId = requestAnimationFrame(gameLoop);
        }
        async function startGame() { if (!selectedCharacter) { messageArea.textContent = "Select a character!";
        return; } if (!audioInitialized) await initializeAudio(); if (typeof Tone !== 'undefined') await Tone.start(); proceedWithStart();
        }
        function proceedWithStart() { 
            isGameRunning=true;
            isGameOver=false; isExploding=false; 
            saucer.active=false; saucer.beamActive=false; saucer.state='idle';
            approachingTopOutcome = null; 
            messageArea.textContent = "Go! Reach the Tree!"; 
            defineTrophy(); generateSafePath(); placeMines(); initializePlayer(); 
            startButton.disabled=true; charButtons.forEach(b=>b.disabled=true);
            leftButton.disabled=false; rightButton.disabled=false; 
            if(animationFrameId) cancelAnimationFrame(animationFrameId); 
            gameLoop(); 
        }
        function resetGameAfterDelay() { leftButton.disabled = true;
        rightButton.disabled = true; moveLeft=false; moveRight=false; setTimeout(resetGame, 3000); }
        
        function resetGame() {
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }
            isGameRunning = false;
            isGameOver = false;
            isExploding = false;
            saucer.active = false;
            saucer.beamActive = false;
            saucer.state = 'idle';
            approachingTopOutcome = null;
            playSound('beam', 'stop');
            player = null;
            mines = [];
            safePathSegments = [];
            updateStatsDisplay();
            messageArea.textContent = "Select character & Start!";
            startButton.disabled = false;
            charButtons.forEach(b => {
                b.disabled = false;
                b.classList.remove('selected');
            });
            selectedCharacter = null;
            leftButton.disabled = true;
            rightButton.disabled = true;
            clearCanvas();
            defineTrophy();
            drawTrophy();
        }
        
        startButton.addEventListener('click', startGame);
        charButtons.forEach(b => { b.addEventListener('click', () => { if(isGameRunning||isGameOver) return; charButtons.forEach(btn=>btn.classList.remove('selected')); b.classList.add('selected'); selectedCharacter = b.dataset.char; messageArea.textContent=`Selected ${selectedCharacter}. Press Start!`; });});
        const handleMove = (key, isDown) => { if(!isGameRunning||isExploding||saucer.state==='beaming') return; if(key==='Left') moveLeft=isDown; if(key==='Right') moveRight=isDown; document.getElementById(key.toLowerCase()+'Button').classList.toggle('keyboard-active', isDown); };
        leftButton.addEventListener('mousedown', ()=>handleMove('Left',true)); leftButton.addEventListener('mouseup', ()=>handleMove('Left',false));
        leftButton.addEventListener('mouseleave', ()=>handleMove('Left',false)); leftButton.addEventListener('touchstart', (e)=>{e.preventDefault();handleMove('Left',true);}); leftButton.addEventListener('touchend',()=>handleMove('Left',false));
        rightButton.addEventListener('mousedown',()=>handleMove('Right',true)); rightButton.addEventListener('mouseup',()=>handleMove('Right',false)); rightButton.addEventListener('mouseleave',()=>handleMove('Right',false)); rightButton.addEventListener('touchstart',(e)=>{e.preventDefault();handleMove('Right',true);}); rightButton.addEventListener('touchend',()=>handleMove('Right',false));
        window.addEventListener('keydown', (e) => { if(e.key==='ArrowLeft') handleMove('Left',true); if(e.key==='ArrowRight') handleMove('Right',true); });
        window.addEventListener('keyup', (e) => { if(e.key==='ArrowLeft') handleMove('Left',false); if(e.key==='ArrowRight') handleMove('Right',false); });

        // 2. RUNTIME: Call the functions to initialize and run the applet.
        debugLog("Applet initializing...");
        if (typeof window.BBS_APPLET_CHECKSUM !== 'undefined') {
             debugLog(`Code Checksum: ${window.BBS_APPLET_CHECKSUM.substring(0, 16)}...`);
        }
        
        const [user, savedData] = await Promise.all([bbs.getUserInfo(), bbs.getData()]);
        debugLog(`User info received for: ${user.username}`);
        const container = document.querySelector('.game-container');
        const welcomeArea = document.createElement('p');
        welcomeArea.textContent = `Welcome, ${user.nickname || user.username}!`;
        welcomeArea.className = 'text-sm text-gray-400 mt-2';
        container.appendChild(welcomeArea);
        
        if (savedData && typeof savedData === 'object' && !Array.isArray(savedData) && savedData !== null) {
            const newStats = { ...stats, ...savedData };
            stats = newStats;
            debugLog("Loaded saved stats from BitSync.");
        } else {
            debugLog("No saved stats found or data was in an invalid format.");
        }
        
        updateStatsDisplay();
        setupUI();
        resetGame();
    } catch (e) {
        messageArea.textContent = "Error initializing with BBS!";
        debugLog(`FATAL ERROR: ${e.message}`);
    }
})();
