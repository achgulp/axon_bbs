// PipeDodger.js - A simple Flappy Bird-style game for Axon BBS applet
// This is a single-file JS applet that runs in a sandboxed iframe.
// It uses the BBS API via postMessage to get user info, load/save data (high score).
// Game mechanics: Tap/click to float up, avoid pipes, score points for passing gaps.
// On game over, save high score if higher.

// Setup BBS API wrappers using postMessage
const bbs = {
  getUserInfo: () => new Promise((resolve) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'userInfo') {
        resolve(e.data.data);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'getUserInfo', id }, '*');
  }),// PipeDodger.js - A simple Flappy Bird-style game for Axon BBS applet
// This is a single-file JS applet that runs in a sandboxed iframe.
// It uses the BBS API via postMessage to get user info, load/save data (high score).
// Game mechanics: Tap/click to float up, avoid pipes, score points for passing gaps.
// On game over, save high score if higher.

// Setup BBS API wrappers using postMessage
const bbs = {
  getUserInfo: () => new Promise((resolve) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'userInfo') {
        resolve(e.data.data);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'getUserInfo', id }, '*');
  }),
  getData: () => new Promise((resolve) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'data') {
        resolve(e.data.data);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'getData', id }, '*');
  }),
  saveData: (newData) => new Promise((resolve) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'saveConfirmation') {
        resolve(e.data.success);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'saveData', data: newData, id }, '*');
  }),
};

// Game variables
let canvas, ctx;
let birdY, birdVelocity, gravity = 0.5, jump = -10;
let pipes = [];
let pipeWidth = 50, pipeGap = 150, pipeSpeed = 2;
let score = 0, highScore = 0;
let gameOver = true;
let userNickname = 'Player';

// Initialize game
async function init() {
  // Create canvas
  canvas = document.createElement('canvas');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  document.body.appendChild(canvas);
  ctx = canvas.getContext('2d');

  // Load user info and data
  try {
    const userInfo = await bbs.getUserInfo();
    userNickname = userInfo.nickname || 'Player';

    const savedData = await bbs.getData();
    highScore = savedData?.score || 0;
  } catch (err) {
    console.error('BBS API error:', err);
  }

  // Event listeners for jump (click/tap or space)
  canvas.addEventListener('click', jumpBird);
  window.addEventListener('keydown', (e) => { if (e.key === ' ') jumpBird(); });

  resetGame();
  requestAnimationFrame(gameLoop);
}

// Reset game state
function resetGame() {
  birdY = canvas.height / 2;
  birdVelocity = 0;
  pipes = [{ x: canvas.width, y: Math.random() * (canvas.height - pipeGap - 200) + 100 }];
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
  pipes.push({ x: canvas.width, y });
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

      // Score when passing pipe
      if (pipe.x + pipeWidth < 50 && pipe.x > 0) { // Assuming bird at x=50
        score++;
      }
    });

    // Generate new pipe every 150 frames or so
    if (pipes[pipes.length - 1].x < canvas.width - 200) {
      generatePipe();
    }

    // Collision checks
    if (birdY > canvas.height || birdY < 0) {
      endGame();
    }
    pipes.forEach(pipe => {
      if (
        (50 + 20 > pipe.x && 50 < pipe.x + pipeWidth) && // Bird x=50, width=20
        (birdY < pipe.y || birdY + 20 > pipe.y + pipeGap) // Bird height=20
      ) {
        endGame();
      }
    });
  }

  // Draw bird (simple circle)
  ctx.fillStyle = 'yellow';
  ctx.beginPath();
  ctx.arc(50, birdY, 10, 0, Math.PI * 2);
  ctx.fill();

  // Draw pipes
  ctx.fillStyle = 'green';
  pipes.forEach(pipe => {
    ctx.fillRect(pipe.x, 0, pipeWidth, pipe.y); // Top pipe
    ctx.fillRect(pipe.x, pipe.y + pipeGap, pipeWidth, canvas.height - (pipe.y + pipeGap)); // Bottom pipe
  });

  // Draw scores
  ctx.fillStyle = 'black';
  ctx.font = '20px Arial';
  ctx.fillText(`Score: ${score}`, 10, 30);
  ctx.fillText(`High: ${highScore} (${userNickname})`, 10, 60);

  if (gameOver) {
    ctx.fillText('Game Over - Tap to Restart', canvas.width / 2 - 150, canvas.height / 2);
  }

  requestAnimationFrame(gameLoop);
}

// End game and save score
async function endGame() {
  gameOver = true;
  if (score > highScore) {
    highScore = score;
    try {
      await bbs.saveData({ score: highScore });
    } catch (err) {
      console.error('Save error:', err);
    }
  }
}

// Start the game
init();
  getData: () => new Promise((resolve) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'data') {
        resolve(e.data.data);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'getData', id }, '*');
  }),
  saveData: (newData) => new Promise((resolve) => {
    const id = Math.random().toString(36).slice(2);
    const handler = (e) => {
      if (e.data.id === id && e.data.type === 'saveConfirmation') {
        resolve(e.data.success);
        window.removeEventListener('message', handler);
      }
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: 'saveData', data: newData, id }, '*');
  }),
};

// Game variables
let canvas, ctx;
let birdY, birdVelocity, gravity = 0.5, jump = -10;
let pipes = [];
let pipeWidth = 50, pipeGap = 150, pipeSpeed = 2;
let score = 0, highScore = 0;
let gameOver = true;
let userNickname = 'Player';

// Initialize game
async function init() {
  // Create canvas
  canvas = document.createElement('canvas');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  document.body.appendChild(canvas);
  ctx = canvas.getContext('2d');

  // Load user info and data
  try {
    const userInfo = await bbs.getUserInfo();
    userNickname = userInfo.nickname || 'Player';

    const savedData = await bbs.getData();
    highScore = savedData?.score || 0;
  } catch (err) {
    console.error('BBS API error:', err);
  }

  // Event listeners for jump (click/tap or space)
  canvas.addEventListener('click', jumpBird);
  window.addEventListener('keydown', (e) => { if (e.key === ' ') jumpBird(); });

  resetGame();
  requestAnimationFrame(gameLoop);
}

// Reset game state
function resetGame() {
  birdY = canvas.height / 2;
  birdVelocity = 0;
  pipes = [{ x: canvas.width, y: Math.random() * (canvas.height - pipeGap - 200) + 100 }];
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
  pipes.push({ x: canvas.width, y });
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

      // Score when passing pipe
      if (pipe.x + pipeWidth < 50 && pipe.x > 0) { // Assuming bird at x=50
        score++;
      }
    });

    // Generate new pipe every 150 frames or so
    if (pipes[pipes.length - 1].x < canvas.width - 200) {
      generatePipe();
    }

    // Collision checks
    if (birdY > canvas.height || birdY < 0) {
      endGame();
    }
    pipes.forEach(pipe => {
      if (
        (50 + 20 > pipe.x && 50 < pipe.x + pipeWidth) && // Bird x=50, width=20
        (birdY < pipe.y || birdY + 20 > pipe.y + pipeGap) // Bird height=20
      ) {
        endGame();
      }
    });
  }

  // Draw bird (simple circle)
  ctx.fillStyle = 'yellow';
  ctx.beginPath();
  ctx.arc(50, birdY, 10, 0, Math.PI * 2);
  ctx.fill();

  // Draw pipes
  ctx.fillStyle = 'green';
  pipes.forEach(pipe => {
    ctx.fillRect(pipe.x, 0, pipeWidth, pipe.y); // Top pipe
    ctx.fillRect(pipe.x, pipe.y + pipeGap, pipeWidth, canvas.height - (pipe.y + pipeGap)); // Bottom pipe
  });

  // Draw scores
  ctx.fillStyle = 'black';
  ctx.font = '20px Arial';
  ctx.fillText(`Score: ${score}`, 10, 30);
  ctx.fillText(`High: ${highScore} (${userNickname})`, 10, 60);

  if (gameOver) {
    ctx.fillText('Game Over - Tap to Restart', canvas.width / 2 - 150, canvas.height / 2);
  }

  requestAnimationFrame(gameLoop);
}

// End game and save score
async function endGame() {
  gameOver = true;
  if (score > highScore) {
    highScore = score;
    try {
      await bbs.saveData({ score: highScore });
    } catch (err) {
      console.error('Save error:', err);
    }
  }
}

// Start the game
init();
