# Axon BBS - Junior Developer Onboarding Guide
## Understanding the Platform Before You Code

**Audience:** Junior AI Developers (Grok, Gemini, etc.)
**Senior Architect:** Claude Code
**Project:** Warzone Lite RTS Game
**Last Updated:** 2025-10-24

---

## READ THIS FIRST

**You are a junior developer on this project.** Your role is to:
- ✅ Follow these instructions EXACTLY
- ✅ Write code according to the specifications
- ✅ Ask questions if anything is unclear
- ✅ Submit your work for senior review
- ❌ DO NOT make architectural decisions on your own
- ❌ DO NOT deviate from the established patterns
- ❌ DO NOT skip steps or take shortcuts

**Your senior architect (Claude Code) will:**
- Review all your code
- Approve each milestone before you proceed
- Help debug issues
- Guide you through complex problems

---

## Part 1: Understanding Axon BBS

### What is Axon BBS?

Axon BBS is a **federated bulletin board system** that runs over Tor. Think of it like a decentralized Reddit where:
- Multiple BBS instances can communicate with each other
- Users are anonymous (identified by public keys)
- Content syncs across trusted instances via BitSync protocol
- Everything is encrypted and routed through Tor

### Key Concepts You MUST Understand

#### 1. Applets

**Definition:** JavaScript applications that run in sandboxed iframes within the BBS.

**Important Facts:**
- Applets are SANDBOXED - they can't access the DOM outside their iframe
- Applets communicate with the BBS via `postMessage` API
- Applets are hosted as attachments and loaded dynamically
- Users run applets by viewing special message board posts

**Example Applets:**
- `AxonChat.js` - Real-time chat
- `hexgl.js` - Racing game
- `FortressOverlord.js` - Strategy game
- `Warzone_Lite.js` - What you'll be building

#### 2. The BBS API (Your Only Way to Talk to Axon BBS)

The applet communicates with the BBS through a JavaScript object called `window.bbs`.

**CRITICAL:** This is the ONLY API available to applets. You cannot:
- Access the file system
- Make arbitrary HTTP requests
- Access localStorage/sessionStorage directly
- Use WebSockets

**Available Functions:**

```javascript
// Get current user information
window.bbs.getUserInfo()
// Returns: { username, pubkey, karma, profile_image_url }

// Get applet-specific persistent data
window.bbs.getData()
// Returns: Object (whatever you saved before)

// Save applet-specific persistent data
window.bbs.saveData(newData)
// Argument: Object to save
// Returns: Promise<void>

// Get information about this applet instance
window.bbs.getAppletInfo()
// Returns: { id, name, parameters: {...} }

// Post an event (for multiplayer)
window.bbs.postEvent({ subject, body })
// Argument: { subject: string, body: string }
// Returns: Promise<void>

// Read events (for multiplayer)
window.bbs.readEvents()
// Returns: Promise<Array<{ id, subject, body, timestamp }>>

// Get attached file as Blob (for assets)
window.bbs.getAttachmentBlob({ hash })
// Argument: { hash: string }
// Returns: Promise<Blob>
```

#### 3. Hybrid Applets (The Pattern You'll Use)

**Definition:** An applet that loads in two stages:

**Stage 1: Loader (Small JavaScript File)**
- The main applet file (e.g., `Warzone_Lite.js`)
- ~50-150KB of JavaScript code
- Contains the BBS API helper
- Contains game logic
- Downloads and unpacks assets

**Stage 2: Asset Package (Large Binary File)**
- A ZIP file containing textures, sounds, models, etc.
- Stored as a FileAttachment on the BBS
- Referenced by hash in applet parameters
- Downloaded and unpacked by the loader

**Why This Pattern?**
- The BBS can handle small applet files efficiently
- Large assets are stored separately via BitSync
- Users can choose to download assets or not
- Multiple applets can share asset packages

**Example Flow:**
```
1. User clicks "Play Warzone Lite"
2. BBS loads Warzone_Lite.js (~150KB) into iframe
3. Applet calls getAppletInfo() → gets asset_hash parameter
4. Applet calls getAttachmentBlob(asset_hash) → downloads 20MB ZIP
5. Applet unpacks ZIP in memory using JSZip
6. Game starts with all assets loaded
```

#### 4. Federation & Real-Time Events

**The Problem:** How do players on different BBS instances play together?

**The Solution:** Event-based messaging via the BBS backend.

**How It Works:**

```javascript
// Player 1 on HostBBS issues a command
await window.bbs.postEvent({
  subject: 'WARZONE_LITE_MP',
  body: JSON.stringify({
    type: 'MOVE_UNIT',
    unitId: 'tank_5',
    targetX: 45,
    targetZ: 30
  })
});

// Player 2 on PiBBS polls for events
const events = await window.bbs.readEvents();
// Returns events from ALL players in the game
// Including players on other BBS instances!

// Player 2 processes the command
events.forEach(event => {
  if (event.subject === 'WARZONE_LITE_MP') {
    const command = JSON.parse(event.body);
    // Execute the command locally
    moveUnit(command.unitId, command.targetX, command.targetZ);
  }
});
```

**Key Points:**
- Events are synchronized across federated BBS instances
- Polling interval: ~2 seconds (this is why we use heartbeat system)
- Events are persistent (stored in database)
- Each event has a unique ID (don't process twice!)

---

## Part 2: Required Reading

Before you write ANY code, you MUST read these files:

### Essential Documentation

1. **`/path/to/axon_bbs/DEVELOPER_HANDBOOK.md`**
   - Read the entire file
   - Pay special attention to the applet sections
   - Understand the security model

2. **`/path/to/axon_bbs/ARCHITECTURE.md`**
   - Understand the overall system architecture
   - Focus on the applet runtime sections
   - Learn how federation works

3. **`/path/to/axon_bbs/docs/AxonBBSAppletDevGuideforAI.txt`**
   - This is YOUR bible for applet development
   - Read it multiple times
   - Reference it constantly

4. **`/path/to/axon_bbs/docs/Applet_Publishing_Guide.md`**
   - How to deploy your applet when complete
   - Testing procedures
   - Publishing workflow

### Reference Applets (Study These!)

**You MUST study these existing applets before writing code:**

#### 1. `/path/to/axon_bbs/frontend/src/applets/hexgl.js`
**Why Study:** Perfect example of hybrid asset loading pattern

**Key Sections to Understand:**
- Lines 25-62: BBS API Helper (YOU MUST COPY THIS EXACTLY)
- Lines 84-120: Asset loading function
- Lines 379-388: Getting applet parameters
- Lines 388: Using `getAttachmentBlob()`

**What to Learn:**
- How to structure the BBS API helper
- How to download and unpack asset ZIP files
- How to use JSZip library
- Progress bar implementation

#### 2. `/path/to/axon_bbs/frontend/src/applets/FortressOverlord.js`
**Why Study:** Example of 3D RTS with multiplayer

**Key Sections to Understand:**
- Lines 1-37: BBS API Helper
- Lines 102-169: Game service for multiplayer events
- Lines 248-400: Three.js game board setup
- Lines 131-169: Event polling and command execution

**What to Learn:**
- How to use Three.js for 3D rendering
- Orthographic camera setup
- Unit movement and combat
- Event-based multiplayer synchronization
- How to structure a game loop

#### 3. `/path/to/axon_bbs/docs/archive/AxonChat_DeveloperHandoff_10.27.0.txt`
**Why Study:** Real-time federation pattern

**Key Sections to Understand:**
- Lines 71-93: Data model for shared state
- Lines 112-123: Chat-specific API usage
- Lines 189-235: Polling mechanism
- Lines 174-186: Sending updates

**What to Learn:**
- How to structure event payloads
- Polling intervals and best practices
- State management for multiplayer
- User presence tracking

---

## Part 3: Development Environment Setup

### Required Tools

1. **Text Editor**
   - VS Code recommended
   - Install "JavaScript (ES6) code snippets" extension
   - Install "ESLint" extension

2. **Browser**
   - Chrome or Firefox
   - Enable Developer Tools (F12)
   - Know how to use Console tab (for debugging)
   - Know how to use Network tab (for monitoring assets)

3. **Command Line Access**
   - You'll need to test on the actual Axon BBS
   - Running at `/path/to/axon_bbs/`
   - Django backend must be running

### File Locations You Need to Know

```
/path/to/axon_bbs/
├── frontend/src/applets/
│   ├── Warzone_Lite.js          ← YOU WILL CREATE THIS
│   ├── hexgl.js                 ← STUDY THIS (hybrid pattern)
│   ├── FortressOverlord.js      ← STUDY THIS (3D RTS)
│   └── AxonChat.js              ← STUDY THIS (federation)
│
├── docs/
│   ├── DEVELOPER_HANDBOOK.md    ← READ THIS
│   ├── ARCHITECTURE.md          ← READ THIS
│   ├── AxonBBSAppletDevGuideforAI.txt  ← READ THIS
│   ├── Applet_Publishing_Guide.md      ← READ THIS
│   ├── Warzone_Lite_Implementation_Plan.md  ← YOUR ROADMAP
│   └── JUNIOR_DEV_TASKS.md      ← YOUR TASK LIST (next file)
│
└── frontend/src/applets/warzone2100/  ← ASSET SOURCE
    └── data/base/
        ├── texpages/  ← Textures to extract
        ├── structs/   ← 3D models to reference
        └── audio/     ← Sounds to extract
```

---

## Part 4: Coding Standards (MUST FOLLOW)

### BBS API Helper (MANDATORY BOILERPLATE)

**YOU MUST include this EXACT code at the top of every applet:**

```javascript
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
      if (window.parent !== window) {
        window.parent.postMessage({ command, payload, requestId }, '*');
      } else {
        console.warn("BBS API: Not running in a frame. Call will be simulated.");
        // Fallback for testing outside iframe
        if (command === 'getUserInfo') {
          resolve({ username: 'test', nickname: 'Test User', pubkey: 'test123' });
        } else if (command === 'getAppletInfo') {
          resolve({ id: 'test', name: 'Test Applet', parameters: {} });
        } else {
          resolve({});
        }
      }
    });
  },
  // Standard API
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); },
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); },
  postEvent: function(eventData) { return this._postMessage('postEvent', eventData); },
  readEvents: function() { return this._postMessage('readEvents'); },
  getAttachmentBlob: function(hash) { return this._postMessage('getAttachmentBlob', { hash }); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---
```

**DO NOT MODIFY THIS CODE.** Copy it exactly as shown.

### Code Structure (MANDATORY PATTERN)

```javascript
// 1. BBS API Helper (see above)
window.bbs = { /* ... exact code above ... */ };

// 2. Main applet execution
(async function() {
  try {
    // 3. Get user and applet info
    const userInfo = await window.bbs.getUserInfo();
    const appletInfo = await window.bbs.getAppletInfo();

    console.log('Warzone Lite: Starting...');
    console.log('User:', userInfo.nickname);
    console.log('Applet ID:', appletInfo.id);

    // 4. Your game initialization code here
    // ...

  } catch (error) {
    console.error('Warzone Lite: Fatal error:', error);
    document.body.innerHTML = `
      <div style="color: red; padding: 20px;">
        <h1>Error Loading Warzone Lite</h1>
        <p>${error.message}</p>
      </div>
    `;
  }
})();
```

### JavaScript Standards

**Style Guide:**
- Use `const` and `let`, NEVER `var`
- Use arrow functions: `() => {}` instead of `function() {}`
- Use template literals: `` `Hello ${name}` `` instead of `'Hello ' + name`
- Always use semicolons
- 2-space indentation
- camelCase for variables: `myVariable`
- PascalCase for classes: `MyClass`
- UPPER_CASE for constants: `MAX_UNITS`

**Error Handling:**
- Always use try/catch around async operations
- Always log errors to console
- Show user-friendly error messages

**Comments:**
- Add comments explaining WHY, not WHAT
- Use JSDoc for function documentation
- Add section headers for major code blocks

### Three.js Standards (For 3D Code)

```javascript
// Import from CDN (don't bundle)
// Load via script tag: https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js

// Standard scene setup pattern
const scene = new THREE.Scene();
const camera = new THREE.OrthographicCamera(/* params */);
const renderer = new THREE.WebGLRenderer({ antialias: true });

// Always enable shadows
renderer.shadowMap.enabled = true;

// Always add lights
const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
directionalLight.castShadow = true;
scene.add(directionalLight);

// Animation loop pattern
function animate() {
  requestAnimationFrame(animate);
  // Update game logic here
  renderer.render(scene, camera);
}
animate();
```

---

## Part 5: Testing Your Code

### Local Testing Checklist

Before submitting code for review, test these:

1. **BBS API Works**
   ```javascript
   // Test in browser console
   await window.bbs.getUserInfo();  // Should return user object
   await window.bbs.getAppletInfo();  // Should return applet info
   ```

2. **No Console Errors**
   - Open DevTools (F12)
   - Check Console tab
   - Should have ZERO red errors

3. **Asset Loading Works**
   - Check Network tab
   - Verify asset ZIP downloads
   - Verify all textures/sounds load

4. **Game Renders**
   - Should see 3D scene
   - Should see units/buildings
   - Should be able to interact

5. **Performance**
   - Check FPS in DevTools
   - Should be 60 FPS with <100 units

### Submission Checklist

Before asking senior dev for review:

- [ ] Code follows the mandatory structure
- [ ] BBS API helper is included exactly as shown
- [ ] All required functions are implemented
- [ ] No console errors
- [ ] Code is commented
- [ ] Tested in actual Axon BBS iframe
- [ ] Screenshots/video of working feature

---

## Part 6: Common Mistakes to Avoid

### ❌ WRONG: Modifying BBS API Helper

```javascript
// DON'T DO THIS
window.bbs = {
  getUserInfo: function() {
    // Custom implementation
  }
};
```

### ✅ CORRECT: Using Provided Helper

```javascript
// Copy the exact helper code provided
window.bbs = { /* exact code from above */ };
```

---

### ❌ WRONG: Trying to Access Parent Window

```javascript
// DON'T DO THIS - Applets are sandboxed!
window.parent.document.getElementById('something');
```

### ✅ CORRECT: Using BBS API

```javascript
// Use the API provided
const userInfo = await window.bbs.getUserInfo();
```

---

### ❌ WRONG: Synchronous Asset Loading

```javascript
// DON'T DO THIS - Will block the thread
const texture = loadTextureSync('texture.png');
```

### ✅ CORRECT: Async Asset Loading

```javascript
// Use async/await
const texture = await loadTextureAsync('texture.png');
```

---

### ❌ WRONG: Forgetting Error Handling

```javascript
// DON'T DO THIS - Will crash on errors
const info = await window.bbs.getUserInfo();
```

### ✅ CORRECT: Always Try/Catch

```javascript
// Always wrap in try/catch
try {
  const info = await window.bbs.getUserInfo();
} catch (error) {
  console.error('Failed to get user info:', error);
}
```

---

### ❌ WRONG: Hardcoding Asset Hashes

```javascript
// DON'T DO THIS
const assetHash = 'abc123...';
```

### ✅ CORRECT: Getting Hash from Parameters

```javascript
// Get from applet info
const appletInfo = await window.bbs.getAppletInfo();
const assetHash = appletInfo.parameters.asset_hash;
```

---

## Part 7: Getting Help

### When You're Stuck

1. **Read the documentation again**
   - 90% of questions are answered in the docs
   - Re-read the relevant sections

2. **Study the reference applets**
   - Find a similar feature in hexgl.js or FortressOverlord.js
   - Copy the pattern

3. **Check the console**
   - What errors are showing?
   - Google the error message

4. **Ask your senior dev (Claude Code)**
   - Explain what you're trying to do
   - Show the error message
   - Show your code
   - Ask specific questions

### Good Questions vs Bad Questions

**❌ Bad Question:**
> "It doesn't work. Help!"

**✅ Good Question:**
> "I'm trying to load the asset package using getAttachmentBlob(), but I'm getting this error: 'TypeError: Cannot read property hash of undefined'. Here's my code: [paste code]. I've verified that appletInfo.parameters exists, but parameters.asset_hash is undefined. What am I missing?"

**❌ Bad Question:**
> "How do I make the game?"

**✅ Good Question:**
> "I've read the FortressOverlord.js file and I see they use OrthographicCamera on line 299. The implementation plan says to use a 45° angle. Should I use the same camera.position.set(10, 30, 10) values, or should I adjust them for the larger 64×80 map?"

---

## Part 8: Your First Task

Once you've read all the required documentation, your first task is:

**TASK 0: Demonstrate Understanding**

Create a simple test applet that:
1. Includes the BBS API helper
2. Gets user info and displays it
3. Gets applet info and displays it
4. Logs "Hello from [username]" to console

Submit this for review before proceeding to actual development.

---

## Summary: Your Role

You are a **junior developer** building Warzone Lite under the guidance of a senior architect.

**Your responsibilities:**
- Follow instructions precisely
- Study reference code before writing new code
- Write clean, tested code
- Ask questions when unclear
- Submit work for review regularly

**Your senior's responsibilities:**
- Provide architecture and design
- Review your code
- Approve milestones
- Debug complex issues
- Make architectural decisions

**Together, we'll build an amazing RTS game for Axon BBS!**

---

**Next Document:** `JUNIOR_DEV_TASKS.md` (Your specific task breakdown)

**Questions?** Ask your senior architect (Claude Code) in the chat.

**Ready to code?** Read the next document and start with Task 0!
