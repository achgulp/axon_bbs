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


// PipeDodger.js - A simple Flappy Bird-style game for Axon BBS applet

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

// Debug log function (like a console overlay)
function debugLog(msg) {
    if (window.BBS_DEBUG_MODE !== true) return;
    const debugDialog = document.getElementById('debug-dialog');
    if (!debugDialog) return;
    const logEntry = document.createElement('div');
    logEntry.textContent = `> ${msg}`;
    debugDialog.appendChild(logEntry);
    debugDialog.scrollTop = debugDialog.scrollHeight; // Auto-scroll
}

// Game variables
let canvas, ctx;
let birdX = 50, birdY, birdVelocity, gravity = 0.5, jump = -10;
let pipes = [];
let pipeWidth = 50, pipeGap = 150, pipeSpeed = 3;
let score = 0, highScore = 0, deaths = 0, wins = 0, losses = 0;
let gameOver = true;
let userNickname = 'Player';
let animationFrameId = null;

// Reset game state
function resetGame() {
  if (!canvas) return; // Guard against premature calls
  birdY = canvas.height / 2;
  birdVelocity = -5; // Initial upward boost for brief hover
  pipes = [{ x: canvas.width, y: Math.random() * (canvas.height - pipeGap - 200) + 100, scored: false }];
  score = 0;
  gameOver = false;
}

// Jump function
function jumpBird() {
  if (gameOver) {
    resetGame();
  } else {
    birdVelocity = jump;
  }
}

// Generate new pipe
function generatePipe() {
  const y = Math.random() * (canvas.height - pipeGap - 200) + 100;
  pipes.push({ x: canvas.width, y, scored: false });
}

// Game loop
function gameLoop() {
  if (!canvas || !ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!gameOver) {
    // Update bird
    birdVelocity += gravity;
    birdY += birdVelocity;

    // Update pipes
    for (let i = pipes.length - 1; i >= 0; i--) {
      let pipe = pipes[i];
      pipe.x -= pipeSpeed;

      if (pipe.x + pipeWidth < 0) {
        pipes.splice(i, 1);
      }

      if (pipe.x + pipeWidth < birdX && !pipe.scored) {
        score += 10;
        pipe.scored = true;
      }
    }

    if (pipes.length === 0 || pipes[pipes.length - 1].x < canvas.width - 250) {
      generatePipe();
    }

    // Collision checks
    if (birdY > canvas.height || birdY < 0) {
      endGame();
    }
    pipes.forEach(pipe => {
      if (
        (birdX + 10 > pipe.x && birdX - 10 < pipe.x + pipeWidth) &&
        (birdY - 10 < pipe.y || birdY + 10 > pipe.y + pipeGap)
      ) {
        endGame();
      }
    });
  }

  // Draw bird (simple circle)
  ctx.fillStyle = 'yellow';
  ctx.beginPath();
  ctx.arc(birdX, birdY, 10, 0, Math.PI * 2);
  ctx.fill();

  // Draw pipes
  ctx.fillStyle = 'green';
  pipes.forEach(pipe => {
    ctx.fillRect(pipe.x, 0, pipeWidth, pipe.y);
    ctx.fillRect(pipe.x, pipe.y + pipeGap, pipeWidth, canvas.height - (pipe.y + pipeGap));
  });

  // Draw scores
  ctx.fillStyle = 'white';
  ctx.font = '24px Arial';
  ctx.textAlign = 'left';
  ctx.fillText(`Score: ${score}`, 10, 30);
  ctx.fillText(`High: ${highScore} (${userNickname})`, 10, 60);

  if (gameOver) {
    ctx.font = '30px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Game Over - Click to Restart', canvas.width / 2, canvas.height / 2);
  }

  animationFrameId = requestAnimationFrame(gameLoop);
}

// End game and save score
async function endGame() {
  if (gameOver) return; // Prevent multiple calls
  gameOver = true;
  losses++;
  deaths++;
  
  // A "win" in this game could be considered surviving to get a score
  if (score > 0) {
      wins++;
  }

  if (score > highScore) {
    highScore = score;
  }

  try {
    debugLog('Saving game data...');
    await bbs.saveData({
      score: highScore,
      wins: wins,
      losses: losses,
      deaths: deaths
    });
    debugLog('Save complete.');
  } catch(e) {
    debugLog(`Save failed: ${e.message}`);
  }
}

// Main initialization function
async function main() {
    // 1. Create HTML and CSS
    const styles = `
        body, html { margin: 0; padding: 0; overflow: hidden; width: 100%; height: 100%; }
        canvas { display: block; background-color: #000; }
        #debug-dialog { display: none; position: absolute; bottom: 10px; left: 10px; width: 250px; height: 150px; background-color: rgba(0,0,0,0.7); border: 1px solid #4a5568; border-radius: 5px; color: #9AE6B4; font-family: monospace; font-size: 10px; overflow-y: scroll; padding: 5px; z-index: 1000; }
    `;
    const styleSheet = document.createElement("style");
    styleSheet.innerText = styles;
    document.head.appendChild(styleSheet);
    
    document.getElementById('applet-root').innerHTML = `
        <canvas id="gameCanvas"></canvas>
        <div id="debug-dialog"></div>
    `;

    // 2. Setup debug console
    if (window.BBS_DEBUG_MODE === true) {
        document.getElementById('debug-dialog').style.display = 'block';
    }
    
    // 3. Setup canvas and event listeners
    canvas = document.getElementById('gameCanvas');
    ctx = canvas.getContext('2d');
    
    const resizeCanvas = () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas(); // Initial size

    canvas.addEventListener('click', jumpBird);
    window.addEventListener('keydown', (e) => { if (e.key === ' ') jumpBird(); });

    // 4. Fetch initial data from BBS
    try {
        debugLog('Fetching initial data...');
        const [userInfo, savedData] = await Promise.all([bbs.getUserInfo(), bbs.getData()]);

        if (userInfo) {
            userNickname = userInfo.nickname || 'Player';
            debugLog(`Welcome, ${userNickname}`);
        }
        if (savedData) {
            highScore = savedData.score || 0;
            wins = savedData.wins || 0;
            losses = savedData.losses || 0;
            deaths = savedData.deaths || 0;
            debugLog(`Loaded high score: ${highScore}`);
        }
    } catch (e) {
        debugLog(`Error initializing with BBS: ${e.message}`);
    }
    
    // 5. Start the game
    resetGame();
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
    gameLoop();
}

// Run the main function
main();
