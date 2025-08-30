// PipeDodger.js - A simple Flappy Bird-style game for Axon BBS applet
// This is a single-file JS applet that runs in a sandboxed iframe.
// It uses the BBS API via postMessage to get user info, load/save data (high score).
// Game mechanics: Tap/click to float up, avoid pipes, score points for passing gaps.
// On game over, save high score if higher.

// Setup BBS API wrappers using postMessage with timeouts (no origin checks to avoid sandbox errors)
const API_TIMEOUT = 5000; // 5 seconds

const bbs = {
  getUserInfo: () => new Promise((resolve, reject) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      // No origin check to prevent "permission denied" in strict sandbox
      if (e.data.id === id && e.data.type === 'userInfo') {
        console.log('Received userInfo:', e.data.data);
        logDebug('getUserInfo success');
        resolve(e.data.data);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'getUserInfo', id }, '*');
    logDebug('Sent getUserInfo request');
    setTimeout(() => {
      window.removeEventListener('message', handler);
      logDebug('getUserInfo timeout');
      reject(new Error('getUserInfo timeout'));
    }, API_TIMEOUT);
  }),
  getData: () => new Promise((resolve, reject) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'data') {
        console.log('Received data:', e.data.data);
        logDebug('getData success');
        resolve(e.data.data);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'getData', id }, '*');
    logDebug('Sent getData request');
    setTimeout(() => {
      window.removeEventListener('message', handler);
      logDebug('getData timeout');
      reject(new Error('getData timeout'));
    }, API_TIMEOUT);
  }),
  saveData: (newData) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'saveConfirmation') {
        console.log('Save confirmation:', e.data.success);
        logDebug(`saveData ${e.data.success ? 'success' : 'failed'}`);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'saveData', data: newData, id }, '*');
    logDebug('Sent saveData request: ' + JSON.stringify(newData));
    // Fire-and-forget; no timeout reject
  },
};

// Debug log array and function (like a console overlay)
let debugLogs = [];
function logDebug(msg) {
  debugLogs.push(msg);
  if (debugLogs.length > 10) debugLogs.shift(); // Keep last 10
}

// Game variables
let canvas, ctx;
let birdX = 50, birdY, birdVelocity, gravity = 0.5, jump = -10; // Added birdX for clarity
let pipes = [];
let pipeWidth = 50, pipeGap = 150, pipeSpeed = 3; // Increased speed for more action
let score = 0, highScore = 0, deaths = 0, wins = 0, losses = 0;
let gameOver = true;
let userNickname = 'Player';

// Initialize game (non-blocking API calls)
function init() {
  // Create canvas
  canvas = document.createElement('canvas');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.style.backgroundColor = '#000'; // Dark background to match BBS UI
  document.body.appendChild(canvas);
  ctx = canvas.getContext('2d');

  // General message listener for debug
  window.addEventListener('message', (e) => {
    logDebug('Incoming msg: ' + JSON.stringify(e.data));
  });

  // Event listeners for jump (click/tap or space)
  canvas.addEventListener('click', jumpBird);
  window.addEventListener('keydown', (e) => { if (e.key === ' ') jumpBird(); });

  // Resize handler for responsiveness
  window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  });

  // Start game immediately
  resetGame();
  requestAnimationFrame(gameLoop);

  // Fetch data in background with fallbacks
  bbs.getUserInfo().then(userInfo => {
    userNickname = userInfo.nickname || 'Player';
  }).catch(err => console.error('getUserInfo failed:', err));

  bbs.getData().then(savedData => {
    highScore = savedData?.score || 0;
    deaths = savedData?.deaths || 0;
    wins = savedData?.wins || 0;
    losses = savedData?.losses || 0;
  }).catch(err => console.error('getData failed:', err));
}

// Reset game state
function resetGame() {
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
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!gameOver) {
    // Update bird
    birdVelocity += gravity;
    birdY += birdVelocity;

    // Update pipes
    pipes.forEach((pipe, index) => {
      pipe.x -= pipeSpeed;

      // Remove off-screen pipes
      if (pipe.x + pipeWidth < 0) {
        pipes.splice(index, 1);
      }

      // Score when passing pipe (10 points per pipe)
      if (pipe.x + pipeWidth < birdX && !pipe.scored) {
        score += 10;
        pipe.scored = true;
      }
    });

    // Generate new pipe more frequently (adjusted threshold)
    if (pipes[pipes.length - 1].x < canvas.width - 150) {
      generatePipe();
    }

    // Collision checks
    if (birdY > canvas.height || birdY < 0) {
      endGame();
    }
    pipes.forEach(pipe => {
      if (
        (birdX + 20 > pipe.x && birdX < pipe.x + pipeWidth) && // Bird width=20
        (birdY < pipe.y || birdY + 20 > pipe.y + pipeGap) // Bird height=20
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
    ctx.fillRect(pipe.x, 0, pipeWidth, pipe.y); // Top pipe
    ctx.fillRect(pipe.x, pipe.y + pipeGap, pipeWidth, canvas.height - (pipe.y + pipeGap)); // Bottom pipe
  });

  // Draw scores (larger, white for visibility)
  ctx.fillStyle = 'white';
  ctx.font = '24px Arial';
  ctx.fillText(`Score: ${score}`, 10, 30);
  ctx.fillText(`High: ${highScore} (${userNickname})`, 10, 60);

  if (gameOver) {
    ctx.fillText('Game Over - Tap to Restart', canvas.width / 2 - 180, canvas.height / 2);
  } else if (score === 0) {
    ctx.fillText('Tap to Jump!', canvas.width / 2 - 100, canvas.height / 2 - 50); // Startup prompt
  }

  // Draw debug console (bottom-left overlay)
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
  ctx.fillRect(10, canvas.height - 120, 300, 110);
  ctx.fillStyle = 'white';
  ctx.font = '12px Arial';
  debugLogs.forEach((log, i) => {
    ctx.fillText(log, 15, canvas.height - 100 + i * 12);
  });

  requestAnimationFrame(gameLoop);
}

// End game and save score
async function endGame() {
  gameOver = true;
  if (score === 0) { // Increment losses/deaths only if didn't pass first pipe
    losses++;
    deaths++;
  } else {
    wins++; // Increment wins for successful runs
  }
  if (score > highScore) {
    highScore = score;
    bbs.saveData({
      score: highScore,
      wins: wins,
      losses: losses,
      kills: 0,
      deaths: deaths,
      assists: 0
    });
  }
}

// Start the game
init();
