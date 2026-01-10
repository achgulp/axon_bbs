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
//
// Mimstris Game Logic:
// MIT License - Copyright (c) 2022 Mims H. Wright


// Full path: axon_bbs/frontend/src/applets/mimstris.js

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
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    // --- Start of Applet Code ---
    try {
        // 1. SETUP: Inject CSS, create HTML, and define all variables and functions first.
        const styles = `
            :root {
                --bg-dark: #1a202c; --bg-medium: #2d3748; --bg-light: #4a5568;
                --border-color: #718096; --text-primary: #e2e8f0; --accent-blue: #4299e1;
            }
            html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; background-color: var(--bg-dark); }
            .app-container {
                display: flex;
                justify-content: center;
                align-items: flex-start;
                gap: 20px;
                padding: 20px;
                font-family: 'Lucida Console', 'Courier New', monospace;
                color: var(--text-primary);
                width: 100%;
                height: 100%;
                box-sizing: border-box;
            }
            #game-canvas {
                border: 2px solid var(--border-color);
                background-color: #00263F;
            }
            .sidebar {
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            .info-panel {
                background-color: var(--bg-medium);
                border: 2px solid var(--border-color);
                padding: 15px;
                border-radius: 8px;
                width: 200px;
                text-align: center;
            }
            .info-panel h2 {
                margin: 0 0 10px 0;
                font-size: 1.2em;
                color: var(--accent-blue);
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 5px;
            }
            .info-panel p {
                margin: 5px 0;
                font-size: 1.1em;
            }
            #next-piece-canvas {
                background-color: #00263F;
                border: 1px solid var(--border-color);
                margin-top: 10px;
            }
            #message-overlay {
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                background-color: rgba(0, 0, 0, 0.7);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                color: white;
                text-align: center;
                z-index: 100;
            }
            #message-overlay h1 { font-size: 3em; margin: 0; }
            #message-overlay p { font-size: 1.2em; margin-top: 10px; }
            #debug-dialog { display: none; position: absolute; bottom: 10px; right: 10px; width: 300px; height: 150px; background-color: rgba(0,0,0,0.8); border: 1px solid #4a5568; border-radius: 5px; color: #9AE6B4; font-family: monospace; font-size: 12px; overflow-y: scroll; padding: 5px; z-index: 1000; }
        `;
        const styleSheet = document.createElement("style");
        styleSheet.innerText = styles;
        document.head.appendChild(styleSheet);

        document.getElementById('applet-root').innerHTML = `
            <div id="debug-dialog"></div>
            <div class="app-container">
                <div class="main-game">
                    <canvas id="game-canvas"></canvas>
                </div>
                <div class="sidebar">
                    <div id="score-panel" class="info-panel">
                        <h2>SCORE</h2>
                        <p id="score-display">0</p>
                        <h2>HIGH SCORE</h2>
                        <p id="highscore-display">0</p>
                    </div>
                    <div id="next-piece-panel" class="info-panel">
                        <h2>NEXT</h2>
                        <canvas id="next-piece-canvas"></canvas>
                    </div>
                    <div id="stats-panel" class="info-panel">
                        <h2>STATS</h2>
                        <p>Level: <span id="level-display">0</span></p>
                        <p>Lines: <span id="lines-display">0</span></p>
                    </div>
                </div>
                <div id="message-overlay" style="display: none;">
                    <h1 id="message-text"></h1>
                    <p id="message-subtext"></p>
                </div>
            </div>
        `;

        const debugDialog = document.getElementById('debug-dialog');
        function debugLog(message) {
            if (window.BBS_DEBUG_MODE !== true) return;
            debugDialog.style.display = 'block';
            const logEntry = document.createElement('div');
            logEntry.textContent = `> ${message}`;
            debugDialog.appendChild(logEntry);
            debugDialog.scrollTop = debugDialog.scrollHeight;
        }
        
        // --- Start Ported Mimstris Logic ---

        // From config.js
        const config = {
            startLevel: 0,
            newLevelEvery: 10,
            boardSize: [12, 20],
            blockSize: 28,
            // *** CHANGE: Increased fall rate values for faster gameplay ***
            initialFallRate: 1.5,
            fallRateLevelModifier: 0.75,
            lateralMovementRate: 6,
            downMovementRate: 20,
            backgroundColor: "#00263F",
            guideColor: "#021c2d",
            showGuideLines: true,
            outlinePieces: true,
            showBlockHighlight: true,
            outlineThickness: 0.08,
            activePieces: "TOJLISZ",
            deterministicMode: false,
            randomSeed: "seed"
        };

        // From pieceLibrary.js
        const pieceLibrary = (() => {
            let id = 0;
            const createPiece = (name, color, matrix) => {
                id++;
                matrix = matrix.map((row) => row.map((value) => (value === 0 ? 0 : id)));
                return { name, id, color, matrix, x: 0, y: 0 };
            };
            return [
                createPiece("T", "#AE81FF", [[0,0,0],[1,1,1],[0,1,0]]),
                createPiece("O", "#e94659", [[1,1],[1,1]]),
                createPiece("J", "#F7FF00", [[0,1,0],[0,1,0],[1,1,0]]),
                createPiece("L", "#2753f1", [[0,1,0],[0,1,0],[0,1,1]]),
                createPiece("I", "#FFB900", [[0,1,0],[0,1,0],[0,1,0],[0,1,0]]),
                createPiece("S", "#FF6728", [[0,1,1],[1,1,0]]),
                createPiece("Z", "#11C5BF", [[1,1,0],[0,1,1]]),
            ];
        })();

        // From matrixUtil.js
        const matrixUtil = {
            createEmptyMatrix: (width, height) => Array.from({ length: height }, () => Array(width).fill(0)),
            detectCollision: (destMatrix, srcMatrix, offsetX = 0, offsetY = 0) => {
                for (let y = 0; y < srcMatrix.length; y++) {
                    for (let x = 0; x < srcMatrix[y].length; x++) {
                        if (srcMatrix[y][x] !== 0) {
                            const destX = x + offsetX;
                            const destY = y + offsetY;
                            if (destY >= destMatrix.length || destX < 0 || destX >= destMatrix[0].length || (destMatrix[destY] && destMatrix[destY][destX] !== 0)) {
                                return true;
                            }
                        }
                    }
                }
                return false;
            },
            combineMatrices: (destMatrix, srcMatrix, offsetX = 0, offsetY = 0) => {
                const newMatrix = destMatrix.map(row => [...row]);
                srcMatrix.forEach((row, y) => {
                    row.forEach((value, x) => {
                        if (value !== 0) {
                            const destY = y + offsetY;
                            const destX = x + offsetX;
                            if (newMatrix[destY]) {
                                newMatrix[destY][destX] = value;
                            }
                        }
                    });
                });
                return newMatrix;
            },
            getFullRows: (matrix) => {
                return matrix.reduce((fullRows, row, rowIndex) => {
                    if (row.every(value => value > 0)) {
                        fullRows.push(rowIndex);
                    }
                    return fullRows;
                }, []);
            },
            removeRowAndShift: (matrix, rowIndex) => {
                matrix.splice(rowIndex, 1);
                matrix.unshift(Array(matrix[0].length).fill(0));
                return matrix;
            },
            rotate: (matrix) => {
                const newMatrix = matrix[0].map((_, colIndex) => matrix.map(row => row[colIndex])).reverse();
                return newMatrix;
            }
        };

        // From canvasRenderer.js
        const canvasRenderer = {
            getColorForID: (id) => (pieceLibrary.find(p => p.id === id) || {}).color,
            clearCanvas: (ctx, color) => {
                ctx.fillStyle = color;
                ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            },
            drawBlock: (ctx, x, y, color) => {
                const bx = x * config.blockSize;
                const by = y * config.blockSize;
                ctx.fillStyle = color;
                ctx.fillRect(bx, by, config.blockSize, config.blockSize);
                if (config.outlinePieces) {
                    ctx.strokeStyle = config.backgroundColor;
                    ctx.lineWidth = config.blockSize * config.outlineThickness;
                    ctx.strokeRect(bx, by, config.blockSize, config.blockSize);
                }
            },
            drawMatrix: (ctx, matrix, offsetX = 0, offsetY = 0) => {
                matrix.forEach((row, y) => {
                    row.forEach((value, x) => {
                        if (value !== 0) {
                            canvasRenderer.drawBlock(ctx, x + offsetX, y + offsetY, canvasRenderer.getColorForID(value));
                        }
                    });
                });
            }
        };

        // --- Game State and Main Logic ---
        const canvas = document.getElementById('game-canvas');
        const ctx = canvas.getContext('2d');
        const nextPieceCanvas = document.getElementById('next-piece-canvas');
        const nextPieceCtx = nextPieceCanvas.getContext('2d');
        
        canvas.width = config.boardSize[0] * config.blockSize;
        canvas.height = config.boardSize[1] * config.blockSize;
        nextPieceCanvas.width = 4 * config.blockSize;
        nextPieceCanvas.height = 4 * config.blockSize;
        
        let gameState = {
            board: null,
            currentPiece: null,
            nextPiece: null,
            score: 0,
            lines: 0,
            level: 0,
            isGameOver: true,
            highScore: 0,
            wins: 0,
            losses: 0
        };

        let lastTime = 0;
        let dropCounter = 0;
        let userNickname = 'Player';
        
        function getFallRate() {
            return 1000 / (config.initialFallRate + gameState.level * config.fallRateLevelModifier);
        }

        function getRandomPiece() {
            const active = pieceLibrary.filter(p => config.activePieces.includes(p.name));
            return JSON.parse(JSON.stringify(active[Math.floor(Math.random() * active.length)]));
        }

        function resetPlayer() {
            gameState.currentPiece = gameState.nextPiece;
            gameState.nextPiece = getRandomPiece();
            gameState.currentPiece.x = Math.floor(config.boardSize[0] / 2) - Math.floor(gameState.currentPiece.matrix[0].length / 2);
            gameState.currentPiece.y = 0;
            if (matrixUtil.detectCollision(gameState.board, gameState.currentPiece.matrix, gameState.currentPiece.x, gameState.currentPiece.y)) {
                endGame();
            }
        }
        
        function playerDrop() {
            const newPiece = { ...gameState.currentPiece, y: gameState.currentPiece.y + 1 };
            if (!matrixUtil.detectCollision(gameState.board, newPiece.matrix, newPiece.x, newPiece.y)) {
                gameState.currentPiece = newPiece;
                dropCounter = 0;
            } else {
                mergePiece();
                resetPlayer();
                checkLines();
            }
        }
        
        // *** NEW: Function for the "hard drop" feature ***
        function playerHardDrop() {
            let piece = gameState.currentPiece;
            while (!matrixUtil.detectCollision(gameState.board, piece.matrix, piece.x, piece.y + 1)) {
                piece.y += 1;
            }
            gameState.currentPiece = piece;
            mergePiece();
            resetPlayer();
            checkLines();
            dropCounter = 0;
        }

        function playerMove(direction) {
            const newPiece = { ...gameState.currentPiece, x: gameState.currentPiece.x + direction };
            if (!matrixUtil.detectCollision(gameState.board, newPiece.matrix, newPiece.x, newPiece.y)) {
                gameState.currentPiece = newPiece;
            }
        }

        function playerRotate() {
            const newPiece = { ...gameState.currentPiece, matrix: matrixUtil.rotate(gameState.currentPiece.matrix) };
            let offsetX = 1;
            while (matrixUtil.detectCollision(gameState.board, newPiece.matrix, newPiece.x, newPiece.y)) {
                newPiece.x += offsetX;
                offsetX = -(offsetX + (offsetX > 0 ? 1 : -1));
                if (offsetX > newPiece.matrix[0].length) {
                    return; // Can't rotate
                }
            }
            gameState.currentPiece = newPiece;
        }

        function mergePiece() {
            gameState.board = matrixUtil.combineMatrices(gameState.board, gameState.currentPiece.matrix, gameState.currentPiece.x, gameState.currentPiece.y);
            gameState.score += 10 + gameState.level;
        }

        function checkLines() {
            const fullRows = matrixUtil.getFullRows(gameState.board);
            if (fullRows.length > 0) {
                fullRows.forEach(rowIndex => {
                    gameState.board = matrixUtil.removeRowAndShift(gameState.board, rowIndex);
                });
                gameState.lines += fullRows.length;
                gameState.score += (100 * Math.pow(2, fullRows.length - 1)) * (gameState.level + 1);
                gameState.level = config.startLevel + Math.floor(gameState.lines / config.newLevelEvery);
            }
        }

        function draw() {
            canvasRenderer.clearCanvas(ctx, config.backgroundColor);
            if (config.showGuideLines) {
                ctx.fillStyle = config.guideColor;
                for (let x = 0; x < config.boardSize[0]; x+=2) {
                    ctx.fillRect(x * config.blockSize, 0, config.blockSize, canvas.height);
                }
            }
            
            if (gameState.board) {
                canvasRenderer.drawMatrix(ctx, gameState.board);
            }

            if (gameState.currentPiece) {
                canvasRenderer.drawMatrix(ctx, gameState.currentPiece.matrix, gameState.currentPiece.x, gameState.currentPiece.y);
            }

            canvasRenderer.clearCanvas(nextPieceCtx, config.backgroundColor);
            if (gameState.nextPiece) {
                const x = Math.floor((nextPieceCanvas.width / config.blockSize - gameState.nextPiece.matrix[0].length) / 2);
                const y = Math.floor((nextPieceCanvas.height / config.blockSize - gameState.nextPiece.matrix.length) / 2);
                canvasRenderer.drawMatrix(nextPieceCtx, gameState.nextPiece.matrix, x, y);
            }
            
            document.getElementById('score-display').textContent = gameState.score;
            document.getElementById('highscore-display').textContent = `${gameState.highScore} (${userNickname})`;
            document.getElementById('level-display').textContent = gameState.level;
            document.getElementById('lines-display').textContent = gameState.lines;
        }

        function update(time = 0) {
            if (gameState.isGameOver) return;
            const deltaTime = time - lastTime;
            lastTime = time;
            dropCounter += deltaTime;
            if (dropCounter > getFallRate()) {
                playerDrop();
            }
            draw();
            requestAnimationFrame(update);
        }

        function showMessage(text, subtext = '') {
            document.getElementById('message-text').textContent = text;
            document.getElementById('message-subtext').textContent = subtext;
            document.getElementById('message-overlay').style.display = 'flex';
        }

        async function endGame() {
            gameState.isGameOver = true;
            showMessage('Game Over', 'Press Enter to play again');
            
            if (gameState.score > 0) gameState.wins++;
            gameState.losses++;
            if (gameState.score > gameState.highScore) {
                gameState.highScore = gameState.score;
            }
            
            try {
                debugLog('Saving game data...');
                await bbs.saveData({ 
                    score: gameState.highScore,
                    wins: gameState.wins, 
                    losses: gameState.losses,
                    lines: gameState.lines, // Custom stat, will be saved but not on main board
                });
                debugLog('Save complete.');
            } catch(e) {
                debugLog(`Save failed: ${e.message}`);
            }
        }

        function startGame() {
            gameState.board = matrixUtil.createEmptyMatrix(...config.boardSize);
            gameState.nextPiece = getRandomPiece();
            resetPlayer();
            gameState.score = 0;
            gameState.lines = 0;
            gameState.level = config.startLevel;
            gameState.isGameOver = false;
            document.getElementById('message-overlay').style.display = 'none';
            update();
        }
        
        // Event Listeners
        document.addEventListener('keydown', event => {
            if (gameState.isGameOver) {
                if (event.key === 'Enter') startGame();
                return;
            }
            // *** CHANGE: Added Space Bar handler for hard drop ***
            if (event.key === ' ' || event.code === 'Space') {
                event.preventDefault(); // Prevents the page from scrolling
                playerHardDrop();
            }
            else if (event.key === 'ArrowLeft') playerMove(-1);
            else if (event.key === 'ArrowRight') playerMove(1);
            else if (event.key === 'ArrowDown') playerDrop();
            else if (event.key === 'ArrowUp') playerRotate();
        });

        // --- RUNTIME ---
        if (window.BBS_DEBUG_MODE === true) {
            document.getElementById('debug-dialog').style.display = 'block';
        }
        debugLog("Mimstris Applet initializing...");

        const [userInfo, savedData] = await Promise.all([bbs.getUserInfo(), bbs.getData()]);
        
        if (userInfo) {
            userNickname = userInfo.nickname || 'Player';
        }
        if (savedData) {
            gameState.highScore = savedData.score || 0;
            gameState.wins = savedData.wins || 0;
            gameState.losses = savedData.losses || 0;
        }

        showMessage('Mimstris', 'Press Enter to start');
        draw();

    } catch (e) {
        document.getElementById('applet-root').innerHTML = `<p style="color: red; font-family: monospace;">Applet Failed to Initialize: ${e.message}</p><pre>${e.stack}</pre>`;
        console.error("Applet execution error:", e);
    }
    // --- End of Applet Code ---
})();
