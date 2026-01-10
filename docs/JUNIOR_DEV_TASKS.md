# Warzone Lite - Junior Developer Task Breakdown
## Detailed Implementation Tasks with Code Templates

**Senior Architect:** Claude Code
**Project:** Warzone Lite RTS
**Prerequisites:** You MUST read `JUNIOR_DEV_ONBOARDING.md` first!

---

## How to Use This Document

Each task below includes:
- **Goal:** What you're building
- **Files:** What files to create/modify
- **Code Template:** Starting code you can copy
- **Implementation Steps:** Exact steps to follow
- **Acceptance Criteria:** How to know you're done
- **Submit for Review:** What to show your senior

**IMPORTANT RULES:**
1. Complete tasks in ORDER (don't skip ahead)
2. Get senior approval before moving to next task
3. Test thoroughly before submitting
4. Ask questions if anything is unclear

---

## TASK 0: Verify Understanding (DO THIS FIRST!)

### Goal
Prove you understand the BBS API and can create a basic applet.

### Files to Create
- `/path/to/axon_bbs/frontend/src/applets/Test_BBS_API.js`

### Code Template

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
        console.warn("BBS API: Not running in a frame.");
        if (command === 'getUserInfo') {
          resolve({ username: 'test', nickname: 'Test User', pubkey: 'test123' });
        } else if (command === 'getAppletInfo') {
          resolve({ id: 'test', name: 'Test', parameters: {} });
        } else {
          resolve({});
        }
      }
    });
  },
  getUserInfo: function() { return this._postMessage('getUserInfo'); },
  getData: function() { return this._postMessage('getData'); },
  saveData: function(newData) { return this._postMessage('saveData', newData); },
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---

// --- Main Execution ---
(async function() {
  try {
    console.log('=== BBS API Test Starting ===');

    // Get user info
    const userInfo = await window.bbs.getUserInfo();
    console.log('User Info:', userInfo);

    // Get applet info
    const appletInfo = await window.bbs.getAppletInfo();
    console.log('Applet Info:', appletInfo);

    // Display on page
    const container = document.getElementById('applet-root');
    container.innerHTML = `
      <div style="padding: 20px; font-family: monospace;">
        <h1>BBS API Test</h1>
        <p>Hello from ${userInfo.nickname}!</p>
        <p>Your pubkey: ${userInfo.pubkey}</p>
        <p>Applet ID: ${appletInfo.id}</p>
        <p style="color: green; font-weight: bold;">✓ BBS API is working!</p>
      </div>
    `;

    console.log('=== BBS API Test Complete ===');

  } catch (error) {
    console.error('BBS API Test Error:', error);
    document.getElementById('applet-root').innerHTML = `
      <div style="padding: 20px; color: red;">
        <h1>Error</h1>
        <p>${error.message}</p>
      </div>
    `;
  }
})();
```

### Implementation Steps

1. Create the file at the path above
2. Copy the template code exactly
3. Save the file
4. (Your senior will help test it in the BBS)

### Acceptance Criteria

- [ ] File created at correct location
- [ ] Code copied exactly from template
- [ ] No syntax errors
- [ ] Console shows "BBS API Test Complete"
- [ ] Page displays user info correctly

### Submit for Review

Post in chat:
```
Task 0 complete! I've created Test_BBS_API.js.
The file is at: /path/to/axon_bbs/frontend/src/applets/Test_BBS_API.js
Ready for senior review.
```

---

## WEEK 1 TASKS: Terrain & Ground Units

### TASK 1.1: Create Warzone_Lite.js Skeleton

### Goal
Create the main applet file with basic Three.js setup.

### Files to Create
- `/path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js`

### Code Template

```javascript
// Warzone Lite v1.0 - Real-Time Strategy for Axon BBS
// Copyright (C) 2025 - Licensed under GPL v3
//
// A JavaScript-native RTS game inspired by Warzone 2100
// Features multi-level terrain and multi-altitude air combat
//
// Full path: /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js

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
        console.warn("BBS API: Not running in a frame.");
        if (command === 'getUserInfo') {
          resolve({ username: 'test', nickname: 'Test', pubkey: 'test123' });
        } else if (command === 'getAppletInfo') {
          resolve({ id: 'test', name: 'Warzone Lite', parameters: {} });
        } else {
          resolve({});
        }
      }
    });
  },
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

// --- Main Applet Execution ---
(async function() {
  try {
    const APPLET_VERSION = 'v1.0 - Initial Development';
    console.log(`Warzone Lite ${APPLET_VERSION}: Starting...`);

    // ═══════════════════════════════════════════════════════
    // STEP 1: Load External Libraries
    // ═══════════════════════════════════════════════════════

    function loadScript(src) {
      return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.crossOrigin = 'anonymous';
        script.onload = () => {
          console.log(`Loaded: ${src.split('/').pop()}`);
          resolve();
        };
        script.onerror = () => reject(new Error(`Failed to load: ${src}`));
        document.head.appendChild(script);
      });
    }

    console.log('Loading Three.js...');
    await loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js');

    if (!window.THREE) {
      throw new Error('Three.js failed to load');
    }

    console.log('Three.js loaded successfully');

    // ═══════════════════════════════════════════════════════
    // STEP 2: Get User and Applet Info
    // ═══════════════════════════════════════════════════════

    const userInfo = await window.bbs.getUserInfo();
    const appletInfo = await window.bbs.getAppletInfo();

    console.log('User:', userInfo.nickname);
    console.log('Applet ID:', appletInfo.id);

    // ═══════════════════════════════════════════════════════
    // STEP 3: Initialize Game Container
    // ═══════════════════════════════════════════════════════

    const appletContainer = document.getElementById('applet-root');
    if (!appletContainer) {
      throw new Error('Applet root element not found');
    }

    // Clear and setup container
    appletContainer.innerHTML = '';
    appletContainer.style.margin = '0';
    appletContainer.style.padding = '0';
    appletContainer.style.width = '100%';
    appletContainer.style.height = '100vh';
    appletContainer.style.overflow = 'hidden';
    appletContainer.style.backgroundColor = '#1a2e40';

    // Create mount point for Three.js
    const mountPoint = document.createElement('div');
    mountPoint.id = 'game-mount';
    mountPoint.style.width = '100%';
    mountPoint.style.height = '100%';
    appletContainer.appendChild(mountPoint);

    console.log('Container initialized');

    // ═══════════════════════════════════════════════════════
    // STEP 4: Three.js Scene Setup
    // ═══════════════════════════════════════════════════════

    console.log('Setting up Three.js scene...');

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a2e40);
    scene.fog = new THREE.Fog(0x1a2e40, 50, 150);

    // Camera (Orthographic for RTS view)
    const aspect = window.innerWidth / window.innerHeight;
    const viewSize = 40;
    const camera = new THREE.OrthographicCamera(
      -viewSize * aspect,
      viewSize * aspect,
      viewSize,
      -viewSize,
      1,
      1000
    );

    // Position camera at 45° angle
    camera.position.set(30, 40, 30);
    camera.lookAt(0, 0, 0);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mountPoint.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(-50, 80, -50);
    directionalLight.castShadow = true;
    directionalLight.shadow.camera.left = -100;
    directionalLight.shadow.camera.right = 100;
    directionalLight.shadow.camera.top = 100;
    directionalLight.shadow.camera.bottom = -100;
    scene.add(directionalLight);

    console.log('Three.js scene setup complete');

    // ═══════════════════════════════════════════════════════
    // STEP 5: Create Test Geometry
    // ═══════════════════════════════════════════════════════

    // Simple ground plane
    const groundGeo = new THREE.PlaneGeometry(80, 80);
    const groundMat = new THREE.MeshStandardMaterial({ color: 0x334155 });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // Test cube (to verify rendering works)
    const cubeGeo = new THREE.BoxGeometry(2, 2, 2);
    const cubeMat = new THREE.MeshPhongMaterial({ color: 0x007bff });
    const cube = new THREE.Mesh(cubeGeo, cubeMat);
    cube.position.set(0, 1, 0);
    cube.castShadow = true;
    scene.add(cube);

    console.log('Test geometry added');

    // ═══════════════════════════════════════════════════════
    // STEP 6: Animation Loop
    // ═══════════════════════════════════════════════════════

    let animationFrameId;

    function animate() {
      animationFrameId = requestAnimationFrame(animate);

      // Rotate test cube
      cube.rotation.y += 0.01;

      // Render
      renderer.render(scene, camera);
    }

    // ═══════════════════════════════════════════════════════
    // STEP 7: Window Resize Handler
    // ═══════════════════════════════════════════════════════

    function onWindowResize() {
      const aspect = window.innerWidth / window.innerHeight;
      camera.left = -viewSize * aspect;
      camera.right = viewSize * aspect;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }

    window.addEventListener('resize', onWindowResize);

    // ═══════════════════════════════════════════════════════
    // STEP 8: Start Game
    // ═══════════════════════════════════════════════════════

    console.log('Starting animation loop...');
    animate();

    console.log(`Warzone Lite ${APPLET_VERSION}: Initialization complete!`);

  } catch (error) {
    console.error('Warzone Lite: Fatal error:', error);
    document.getElementById('applet-root').innerHTML = `
      <div style="color: #ef4444; padding: 20px; font-family: monospace;">
        <h1>Warzone Lite - Error</h1>
        <p><strong>Error:</strong> ${error.message}</p>
        <p><strong>Stack:</strong></p>
        <pre style="background: #000; padding: 10px; overflow: auto;">${error.stack}</pre>
      </div>
    `;
  }
})();
```

### Implementation Steps

1. Create the file: `/path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js`
2. Copy the entire template code above
3. Save the file
4. Review the code - make sure you understand each section
5. Don't modify anything yet - this is the baseline

### Acceptance Criteria

- [ ] File created at correct path
- [ ] Code is exactly as provided (no modifications)
- [ ] No syntax errors
- [ ] Understand what each STEP section does

### Submit for Review

```
Task 1.1 complete! Created Warzone_Lite.js skeleton.
File location: /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js
Code includes:
- BBS API helper
- Three.js loading
- Basic scene setup
- Test cube rendering

Ready for testing and review.
```

---

### TASK 1.2: Implement Terrain Heightmap Generation

### Goal
Replace the flat ground plane with a multi-level heightmap terrain.

### What to Modify
In `Warzone_Lite.js`, find STEP 5 (Create Test Geometry) and replace it with this:

### Code to Add

```javascript
// ═══════════════════════════════════════════════════════
// STEP 5: Terrain System
// ═══════════════════════════════════════════════════════

console.log('Generating terrain...');

const TerrainSystem = {
  size: { width: 64, depth: 80 },
  heightLevels: 8,
  heightMap: null,
  mesh: null,

  // Simple 2D noise function
  noise2D(x, y) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453;
    return (n - Math.floor(n)) * 2 - 1;  // -1 to 1
  },

  // Generate Perlin-like noise
  generatePerlinNoise(width, height, scale) {
    const noise = [];
    for (let z = 0; z < height; z++) {
      noise[z] = [];
      for (let x = 0; x < width; x++) {
        let value = 0;
        let amplitude = 1;
        let frequency = 1 / scale;

        // Multiple octaves for natural look
        for (let octave = 0; octave < 3; octave++) {
          value += this.noise2D(x * frequency, z * frequency) * amplitude;
          frequency *= 2;
          amplitude *= 0.5;
        }

        noise[z][x] = (value + 1) / 2;  // Normalize to 0-1
      }
    }
    return noise;
  },

  // Generate strategic heightmap
  generateHeightMap() {
    const map = [];
    const noise = this.generatePerlinNoise(this.size.width, this.size.depth, 4);

    for (let z = 0; z < this.size.depth; z++) {
      map[z] = [];
      for (let x = 0; x < this.size.width; x++) {
        // Base height from noise
        let height = Math.floor(noise[z][x] * 3);

        // Strategic features:

        // 1. Center plateau (high ground objective)
        const centerX = this.size.width / 2;
        const centerZ = this.size.depth / 2;
        const distFromCenter = Math.sqrt(
          Math.pow(x - centerX, 2) +
          Math.pow(z - centerZ, 2)
        );

        if (distFromCenter < 8) {
          height = 5;  // Plateau
        } else if (distFromCenter < 10) {
          height = 3;  // Slopes
        }

        // 2. Flat starting zones in corners
        const inTopLeft = (x < 10 && z < 10);
        const inTopRight = (x > 54 && z < 10);
        const inBottomLeft = (x < 10 && z > 70);
        const inBottomRight = (x > 54 && z > 70);

        if (inTopLeft || inTopRight || inBottomLeft || inBottomRight) {
          height = 1;  // Flat for bases
        }

        // 3. Valley choke point
        if (x === 32 && z > 20 && z < 60) {
          height = 0;  // Low valley
        }

        // Clamp to valid range
        map[z][x] = Math.max(0, Math.min(this.heightLevels, height));
      }
    }

    return map;
  },

  // Create terrain mesh
  generate() {
    // Create plane geometry with subdivisions
    const geometry = new THREE.PlaneGeometry(
      this.size.width,
      this.size.depth,
      this.size.width - 1,
      this.size.depth - 1
    );

    // Rotate to horizontal
    geometry.rotateX(-Math.PI / 2);

    // Generate heightmap
    this.heightMap = this.generateHeightMap();

    // Apply heights to vertices
    const positions = geometry.attributes.position;
    for (let i = 0; i < positions.count; i++) {
      const x = Math.floor(i % this.size.width);
      const z = Math.floor(i / this.size.width);
      const height = this.heightMap[z] ? this.heightMap[z][x] : 0;

      // Y is "up" in Three.js
      positions.setY(i, height);
    }

    // Recompute normals for lighting
    geometry.computeVertexNormals();

    // Create material with height-based coloring
    const material = new THREE.MeshStandardMaterial({
      color: 0x6B8E23,  // Olive green base
      roughness: 0.8,
      metalness: 0.2,
      vertexColors: false
    });

    // Create mesh
    this.mesh = new THREE.Mesh(geometry, material);
    this.mesh.receiveShadow = true;
    this.mesh.name = 'terrain';

    return this.mesh;
  },

  // Get height at world position
  getHeightAt(x, z) {
    const tileX = Math.floor(x + this.size.width / 2);
    const tileZ = Math.floor(z + this.size.depth / 2);

    if (tileX < 0 || tileX >= this.size.width ||
        tileZ < 0 || tileZ >= this.size.depth) {
      return 0;
    }

    return this.heightMap[tileZ][tileX];
  }
};

// Generate and add terrain to scene
const terrain = TerrainSystem.generate();
scene.add(terrain);

console.log('Terrain generated with',
  TerrainSystem.size.width * TerrainSystem.size.depth, 'vertices');

// Update test cube to sit on terrain
const cubeHeight = TerrainSystem.getHeightAt(0, 0);
cube.position.y = cubeHeight + 1;

console.log('Test cube placed at height:', cubeHeight);
```

### Implementation Steps

1. Open `Warzone_Lite.js`
2. Find the line `// STEP 5: Create Test Geometry`
3. **DELETE** the old ground plane code (the PlaneGeometry part)
4. **KEEP** the test cube code
5. **INSERT** the new terrain code above
6. Update the cube position as shown at the bottom
7. Save the file

### Acceptance Criteria

- [ ] Old flat ground is removed
- [ ] New terrain code is added
- [ ] Test cube now sits on terrain (not floating)
- [ ] Console shows "Terrain generated with 5120 vertices"
- [ ] Terrain has visible hills and valleys
- [ ] Center plateau is visible
- [ ] Corner starting zones are flat

### Submit for Review

```
Task 1.2 complete! Implemented heightmap terrain.
Changes:
- Replaced flat ground with 64×80 heightmap
- Added Perlin noise generation
- Created strategic features (plateau, valleys, starting zones)
- Test cube now follows terrain height

The terrain has:
- 5,120 vertices (64×80 grid)
- Heights from 0-8
- Center plateau at height 5
- Flat corners for bases at height 1
- Valley choke point at height 0

Ready for review. Should I proceed to Task 1.3?
```

---

### TASK 1.3: Create Ground Unit System

### Goal
Add ground units (Tank, Artillery, Scout) that follow terrain elevation.

### What to Add
After the TerrainSystem code in STEP 5, add this new system:

### Code to Add

```javascript
// ═══════════════════════════════════════════════════════
// UNIT SYSTEM
// ═══════════════════════════════════════════════════════

console.log('Initializing unit system...');

// Unit statistics
const UNIT_STATS = {
  TANK: {
    cost: 150,
    health: 100,
    damage: 15,
    range: 3,
    speed: 2.5,
    type: 'ground'
  },
  ARTILLERY: {
    cost: 200,
    health: 80,
    damage: 30,
    range: 8,
    speed: 1.5,
    type: 'ground'
  },
  SCOUT: {
    cost: 75,
    health: 50,
    damage: 8,
    range: 2,
    speed: 4,
    type: 'ground'
  }
};

// Player colors
const PLAYER_COLORS = [0x007bff, 0xff4136, 0x2ecc40, 0xffdc00];

const UnitSystem = {
  units: [],
  nextUnitId: 0,

  // Create a new unit
  createUnit(type, x, z, ownerId) {
    const stats = UNIT_STATS[type];
    if (!stats) {
      console.error('Unknown unit type:', type);
      return null;
    }

    const unit = {
      id: `unit_${this.nextUnitId++}`,
      type: type,
      ownerId: ownerId,
      health: stats.health,
      maxHealth: stats.health,
      position: { x, y: 0, z },
      rotation: 0,
      mesh: null,
      targetPosition: null,
      isMoving: false
    };

    // Create 3D mesh
    unit.mesh = this.createMesh(type, ownerId);

    // Position on terrain
    this.updateUnitHeight(unit);

    // Add to scene and tracking array
    scene.add(unit.mesh);
    this.units.push(unit);

    console.log(`Created ${type} unit #${unit.id} for player ${ownerId}`);

    return unit;
  },

  // Create 3D mesh for unit
  createMesh(type, ownerId) {
    let geometry;

    switch (type) {
      case 'TANK':
        geometry = new THREE.BoxGeometry(1.5, 0.8, 2);
        break;
      case 'ARTILLERY':
        geometry = new THREE.CylinderGeometry(0.5, 0.8, 2, 8);
        break;
      case 'SCOUT':
        geometry = new THREE.BoxGeometry(1, 0.4, 1.5);
        break;
      default:
        geometry = new THREE.BoxGeometry(1, 1, 1);
    }

    const material = new THREE.MeshPhongMaterial({
      color: PLAYER_COLORS[ownerId],
      emissive: 0x222222,
      specular: 0x333333
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.userData = { unitId: null };  // Will be set when unit is created

    return mesh;
  },

  // Update unit's Y position to match terrain
  updateUnitHeight(unit) {
    const terrainHeight = TerrainSystem.getHeightAt(
      unit.position.x - TerrainSystem.size.width / 2,
      unit.position.z - TerrainSystem.size.depth / 2
    );

    // Ground units sit on terrain
    const heightOffset = 0.5;  // Half their height
    unit.position.y = terrainHeight + heightOffset;

    // Update mesh position
    unit.mesh.position.set(
      unit.position.x,
      unit.position.y,
      unit.position.z
    );

    unit.mesh.rotation.y = unit.rotation;
  },

  // Move unit toward target
  moveUnit(unit, targetX, targetZ) {
    unit.targetPosition = { x: targetX, z: targetZ };
    unit.isMoving = true;
  },

  // Update all units (called every frame)
  update(deltaTime) {
    this.units.forEach(unit => {
      if (unit.isMoving && unit.targetPosition) {
        const stats = UNIT_STATS[unit.type];
        const speed = stats.speed * deltaTime;

        const dx = unit.targetPosition.x - unit.position.x;
        const dz = unit.targetPosition.z - unit.position.z;
        const distance = Math.sqrt(dx * dx + dz * dz);

        if (distance < speed) {
          // Reached target
          unit.position.x = unit.targetPosition.x;
          unit.position.z = unit.targetPosition.z;
          unit.isMoving = false;
          unit.targetPosition = null;
        } else {
          // Move toward target
          const moveX = (dx / distance) * speed;
          const moveZ = (dz / distance) * speed;

          unit.position.x += moveX;
          unit.position.z += moveZ;

          // Update rotation to face direction
          unit.rotation = Math.atan2(dx, dz);
        }

        // Update height to follow terrain
        this.updateUnitHeight(unit);
      }
    });
  },

  // Get unit by ID
  getUnitById(id) {
    return this.units.find(u => u.id === id);
  },

  // Remove unit
  removeUnit(unit) {
    scene.remove(unit.mesh);
    const index = this.units.indexOf(unit);
    if (index > -1) {
      this.units.splice(index, 1);
    }
  }
};

// Create test units
const testTank = UnitSystem.createUnit('TANK', -10, -10, 0);
const testArtillery = UnitSystem.createUnit('ARTILLERY', 10, -10, 1);
const testScout = UnitSystem.createUnit('SCOUT', 0, 10, 0);

// Make one unit move (for testing)
UnitSystem.moveUnit(testScout, 10, 10);

console.log('Unit system initialized with', UnitSystem.units.length, 'test units');
```

### Then Update the Animation Loop

Find the `animate()` function and update it:

```javascript
// ═══════════════════════════════════════════════════════
// STEP 6: Animation Loop
// ═══════════════════════════════════════════════════════

let animationFrameId;
let lastTime = Date.now();

function animate() {
  animationFrameId = requestAnimationFrame(animate);

  // Calculate delta time
  const now = Date.now();
  const deltaTime = (now - lastTime) / 1000;  // Convert to seconds
  lastTime = now;

  // Update units
  UnitSystem.update(deltaTime);

  // Render
  renderer.render(scene, camera);
}
```

### Implementation Steps

1. Find where terrain code ends (after `scene.add(terrain);`)
2. Add the Unit System code
3. Find the `animate()` function
4. Replace it with the updated version above
5. Remove or comment out the spinning cube code (you don't need it anymore)
6. Save the file

### Acceptance Criteria

- [ ] Code added without syntax errors
- [ ] Console shows "Unit system initialized with 3 test units"
- [ ] Can see 3 units on the terrain (different colors)
- [ ] Units are sitting ON the terrain (not floating)
- [ ] Scout unit moves from (0,10) to (10,10)
- [ ] Moving unit follows terrain as it moves

### Submit for Review

```
Task 1.3 complete! Implemented ground unit system.

Added:
- UNIT_STATS for Tank, Artillery, Scout
- UnitSystem with create/move/update functions
- Terrain-following logic
- 3 test units (different types and players)
- Movement system with smooth interpolation

Units correctly:
- Follow terrain elevation
- Move smoothly
- Rotate to face direction
- Different geometries per type

Ready for review. Should I continue to Task 1.4?
```

---

## STOPPING POINT FOR REVIEW

**Junior Developer:** This is your first checkpoint. Complete Tasks 0, 1.1, 1.2, and 1.3, then **STOP** and submit for review.

**DO NOT PROCEED** until your senior architect (Claude Code) has:
1. Reviewed your code
2. Tested the applet
3. Approved your work
4. Told you to continue

---

## WEEK 2 TASKS: Air Units & Altitude System

**Prerequisites:** Tasks 0, 1.1, 1.2, 1.3 must be complete and approved

---

### TASK 2.1: Implement Altitude System

### Goal
Add altitude levels (0-10) for air units to fly at different heights above terrain.

### What to Add
After the UnitSystem, add the AltitudeSystem:

### Code Template

```javascript
// ═══════════════════════════════════════════════════════
// ALTITUDE SYSTEM (For Air Units)
// ═══════════════════════════════════════════════════════

console.log('Initializing altitude system...');

const AltitudeSystem = {
  // Altitude levels: 0 = ground, 1-3 = low, 4-7 = medium, 8-10 = high
  maxAltitude: 10,
  altitudeLevelHeight: 2,  // Each altitude level = 2 units high

  // Convert altitude level to Y position
  getYPosition(terrainHeight, altitudeLevel) {
    return terrainHeight + (altitudeLevel * this.altitudeLevelHeight);
  },

  // Check if two units can collide (same altitude level)
  canCollide(unit1, unit2) {
    // Ground units are always at altitude 0
    const alt1 = unit1.altitude || 0;
    const alt2 = unit2.altitude || 0;

    // Same altitude level = can collide
    return alt1 === alt2;
  },

  // Get valid altitude range for unit type
  getAltitudeRange(unitType) {
    const ranges = {
      'TANK': { min: 0, max: 0 },        // Ground only
      'ARTILLERY': { min: 0, max: 0 },   // Ground only
      'SCOUT': { min: 0, max: 0 },       // Ground only
      'VTOL': { min: 1, max: 5 },        // Low to medium
      'FIGHTER': { min: 3, max: 10 },    // Medium to high
      'BOMBER': { min: 2, max: 8 }       // Low to high
    };

    return ranges[unitType] || { min: 0, max: 0 };
  },

  // Change unit altitude (for air units)
  setAltitude(unit, newAltitude) {
    const range = this.getAltitudeRange(unit.type);

    // Clamp to valid range
    unit.altitude = Math.max(range.min, Math.min(range.max, newAltitude));

    // Update Y position
    const terrainHeight = TerrainSystem.getHeightAt(unit.position.x, unit.position.z);
    unit.position.y = this.getYPosition(terrainHeight, unit.altitude);

    console.log(`${unit.type} #${unit.id} altitude set to ${unit.altitude}`);
  }
};

console.log('✅ Altitude system initialized');
console.log('   Altitude levels: 0 (ground) to 10 (high)');
console.log('   Level height: 2 units');
```

### Implementation Steps

1. Open `Warzone_Lite.js`
2. Find the end of the UnitSystem code
3. Add the AltitudeSystem code above
4. Save the file

### Acceptance Criteria

- [ ] AltitudeSystem added without syntax errors
- [ ] Console shows "✅ Altitude system initialized"
- [ ] Can call `AltitudeSystem.getAltitudeRange('FIGHTER')`
- [ ] Altitude ranges defined for all unit types

### Submit for Review

```
Task 2.1 complete! Implemented altitude system.

Added:
- AltitudeSystem with 11 altitude levels (0-10)
- Each level = 2 units high
- Altitude ranges per unit type
- Collision detection based on altitude
- setAltitude() function for air units

Ready for Task 2.2 (Air unit types).
```

---

### TASK 2.2: Add Air Unit Types (VTOL, Fighter, Bomber)

### Goal
Add three air unit types with different characteristics and geometries.

### What to Modify
Update UNIT_STATS and UnitSystem.createMesh():

### Code Changes

**Step 1: Add air unit stats to UNIT_STATS:**

```javascript
const UNIT_STATS = {
  // ... existing ground units ...

  // Air units (Week 2)
  VTOL: {
    cost: 250,
    health: 70,
    damage: 12,
    range: 4,
    speed: 3.5,
    type: 'air',
    defaultAltitude: 3
  },
  FIGHTER: {
    cost: 300,
    health: 60,
    damage: 20,
    range: 5,
    speed: 6,
    type: 'air',
    defaultAltitude: 7
  },
  BOMBER: {
    cost: 400,
    health: 90,
    damage: 40,
    range: 6,
    speed: 2,
    type: 'air',
    defaultAltitude: 5
  }
};
```

**Step 2: Update UnitSystem.createMesh() to handle air units:**

Find the `createMesh(type, ownerId)` function and add these cases to the switch statement:

```javascript
createMesh(type, ownerId) {
  let geometry;

  switch (type) {
    // ... existing ground unit cases ...

    case 'VTOL':
      // Diamond/wedge shape for VTOL
      geometry = new THREE.ConeGeometry(0.6, 1.5, 4);
      geometry.rotateX(Math.PI / 2);  // Point forward
      break;

    case 'FIGHTER':
      // Sleek arrow shape for fighter
      geometry = new THREE.ConeGeometry(0.4, 2, 3);
      geometry.rotateX(Math.PI / 2);  // Point forward
      break;

    case 'BOMBER':
      // Wide box for bomber
      geometry = new THREE.BoxGeometry(2, 0.5, 1.5);
      break;

    default:
      geometry = new THREE.BoxGeometry(1, 1, 1);
  }

  const material = new THREE.MeshPhongMaterial({
    color: PLAYER_COLORS[ownerId],
    emissive: 0x222222,
    specular: 0x333333
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.castShadow = true;
  mesh.userData = { unitId: null };

  return mesh;
}
```

**Step 3: Update createUnit() to set initial altitude for air units:**

Find the `createUnit()` function and add after creating the unit object:

```javascript
createUnit(type, x, z, ownerId) {
  const stats = UNIT_STATS[type];
  if (!stats) {
    console.error('Unknown unit type:', type);
    return null;
  }

  const unit = {
    id: `unit_${this.nextUnitId++}`,
    type: type,
    ownerId: ownerId,
    health: stats.health,
    maxHealth: stats.health,
    position: { x, y: 0, z },
    rotation: 0,
    altitude: 0,  // NEW: Track altitude level
    mesh: null,
    targetPosition: null,
    isMoving: false
  };

  // Create 3D mesh
  unit.mesh = this.createMesh(type, ownerId);

  // Position on terrain
  this.updateUnitHeight(unit);

  // NEW: Set altitude for air units
  if (stats.type === 'air' && stats.defaultAltitude) {
    AltitudeSystem.setAltitude(unit, stats.defaultAltitude);
  }

  // Add to scene and tracking array
  scene.add(unit.mesh);
  this.units.push(unit);

  console.log(`Created ${type} unit #${unit.id} for player ${ownerId}`);

  return unit;
}
```

**Step 4: Create test air units:**

After the existing test units, add:

```javascript
// Create test air units
const testVTOL = UnitSystem.createUnit('VTOL', -5, 5, 0);
const testFighter = UnitSystem.createUnit('FIGHTER', 5, 5, 1);
const testBomber = UnitSystem.createUnit('BOMBER', 0, -5, 2);

console.log('Unit system initialized with', UnitSystem.units.length, 'units (ground + air)');
```

### Implementation Steps

1. Add air unit stats to UNIT_STATS
2. Update createMesh() with air unit geometries
3. Add altitude field to createUnit()
4. Set default altitude for air units
5. Create 3 test air units
6. Save the file

### Acceptance Criteria

- [ ] Air unit stats added
- [ ] VTOL uses cone geometry (diamond shape)
- [ ] Fighter uses thin cone (arrow shape)
- [ ] Bomber uses wide box
- [ ] Test units spawn at correct altitudes
- [ ] Console shows "6 units (ground + air)"
- [ ] Air units visible floating above terrain

### Submit for Review

```
Task 2.2 complete! Added air unit types.

Implemented:
- VTOL, Fighter, Bomber unit stats
- Unique geometries for each air unit
- Altitude assignment on creation
- 3 test air units spawned

Can see:
- VTOL at altitude 3 (6 units high)
- Fighter at altitude 7 (14 units high)
- Bomber at altitude 5 (10 units high)

Ready for Task 2.3 (3D pathfinding).
```

---

### TASK 2.3: Implement 3D Pathfinding for Air Units

### Goal
Extend A* pathfinding to support altitude changes for air units.

### What to Modify
Update PathfindingSystem to handle 3D movement:

### Code to Add

Add this new function to PathfindingSystem:

```javascript
// 3D pathfinding for air units (includes altitude)
findPath3D(startX, startZ, startAlt, goalX, goalZ, goalAlt, unitType) {
  const startGrid = this.worldToGrid(startX, startZ);
  const goalGrid = this.worldToGrid(goalX, goalZ);

  const altRange = AltitudeSystem.getAltitudeRange(unitType);

  // Validate positions
  if (!this.isValidPosition(startGrid.x, startGrid.z) ||
      !this.isValidPosition(goalGrid.x, goalGrid.z)) {
    console.warn('3D Pathfinding: Invalid start or goal position');
    return null;
  }

  // Node structure: { x, z, alt, g, h, f, parent }
  const openList = [];
  const closedList = new Set();

  const startNode = {
    x: startGrid.x,
    z: startGrid.z,
    alt: startAlt,
    g: 0,
    h: this.heuristic3D(startGrid.x, startGrid.z, startAlt, goalGrid.x, goalGrid.z, goalAlt),
    f: 0,
    parent: null
  };
  startNode.f = startNode.g + startNode.h;
  openList.push(startNode);

  // 26-directional movement (8 horizontal + up + down for each)
  const directions = [];
  for (let dx = -1; dx <= 1; dx++) {
    for (let dz = -1; dz <= 1; dz++) {
      for (let dalt = -1; dalt <= 1; dalt++) {
        if (dx === 0 && dz === 0 && dalt === 0) continue;  // Skip self
        directions.push({ dx, dz, dalt });
      }
    }
  }

  let iterations = 0;
  const maxIterations = 5000;

  while (openList.length > 0 && iterations < maxIterations) {
    iterations++;

    // Find node with lowest f score
    let currentIndex = 0;
    for (let i = 1; i < openList.length; i++) {
      if (openList[i].f < openList[currentIndex].f) {
        currentIndex = i;
      }
    }

    const current = openList[currentIndex];

    // Check if reached goal
    if (current.x === goalGrid.x && current.z === goalGrid.z && current.alt === goalAlt) {
      // Reconstruct path
      const path = [];
      let node = current;
      while (node !== null) {
        const world = this.gridToWorld(node.x, node.z);
        path.unshift({ x: world.x, z: world.z, alt: node.alt });
        node = node.parent;
      }
      console.log(`✅ Found 3D path with ${path.length} waypoints (${iterations} iterations)`);
      return path;
    }

    // Move current from open to closed
    openList.splice(currentIndex, 1);
    closedList.add(`${current.x},${current.z},${current.alt}`);

    // Check all neighbors
    for (const dir of directions) {
      const neighborX = current.x + dir.dx;
      const neighborZ = current.z + dir.dz;
      const neighborAlt = current.alt + dir.dalt;
      const neighborKey = `${neighborX},${neighborZ},${neighborAlt}`;

      // Validate altitude range
      if (neighborAlt < altRange.min || neighborAlt > altRange.max) continue;

      // Skip if already evaluated or invalid position
      if (closedList.has(neighborKey) || !this.isValidPosition(neighborX, neighborZ)) {
        continue;
      }

      // Calculate cost (altitude changes cost more)
      let movementCost = 1.0;
      if (dir.dx !== 0 && dir.dz !== 0) movementCost *= 1.414;  // Diagonal
      if (dir.dalt !== 0) movementCost += 2;  // Altitude change penalty

      const gScore = current.g + movementCost;

      // Check if neighbor in open list
      let neighborNode = openList.find(n =>
        n.x === neighborX && n.z === neighborZ && n.alt === neighborAlt
      );

      if (!neighborNode) {
        neighborNode = {
          x: neighborX,
          z: neighborZ,
          alt: neighborAlt,
          g: gScore,
          h: this.heuristic3D(neighborX, neighborZ, neighborAlt, goalGrid.x, goalGrid.z, goalAlt),
          f: 0,
          parent: current
        };
        neighborNode.f = neighborNode.g + neighborNode.h;
        openList.push(neighborNode);
      } else if (gScore < neighborNode.g) {
        neighborNode.g = gScore;
        neighborNode.f = neighborNode.g + neighborNode.h;
        neighborNode.parent = current;
      }
    }
  }

  console.warn('⚠️ No 3D path found or max iterations reached');
  return null;
},

// 3D heuristic (Manhattan distance including altitude)
heuristic3D(x, z, alt, goalX, goalZ, goalAlt) {
  return Math.abs(x - goalX) + Math.abs(z - goalZ) + Math.abs(alt - goalAlt) * 2;
}
```

### Update UnitSystem.moveUnit() to use 3D pathfinding:

```javascript
moveUnit(unit, targetX, targetZ, targetAlt) {
  const stats = UNIT_STATS[unit.type];

  // Use 3D pathfinding for air units
  if (stats.type === 'air') {
    const path = PathfindingSystem.findPath3D(
      unit.position.x,
      unit.position.z,
      unit.altitude,
      targetX,
      targetZ,
      targetAlt || unit.altitude,  // Keep current altitude if not specified
      unit.type
    );

    if (path && path.length > 1) {
      unit.path = path;
      unit.currentWaypoint = 1;
      unit.targetPosition = unit.path[unit.currentWaypoint];
      unit.isMoving = true;
      console.log(`Air unit ${unit.id} starting 3D path with ${path.length} waypoints`);
    }
  } else {
    // Ground units use 2D pathfinding (existing code)
    const path = PathfindingSystem.findPath(
      unit.position.x,
      unit.position.z,
      targetX,
      targetZ
    );
    // ... rest of existing ground pathfinding ...
  }
}
```

### Update UnitSystem.update() to handle altitude in movement:

```javascript
update(deltaTime) {
  this.units.forEach(unit => {
    if (unit.isMoving && unit.targetPosition) {
      const stats = UNIT_STATS[unit.type];
      const speed = stats.speed * deltaTime;

      const dx = unit.targetPosition.x - unit.position.x;
      const dz = unit.targetPosition.z - unit.position.z;
      const distance = Math.sqrt(dx * dx + dz * dz);

      if (distance < speed) {
        // Reached waypoint
        unit.position.x = unit.targetPosition.x;
        unit.position.z = unit.targetPosition.z;

        // Update altitude for air units
        if (unit.targetPosition.alt !== undefined) {
          AltitudeSystem.setAltitude(unit, unit.targetPosition.alt);
        }

        // Move to next waypoint
        if (unit.path.length > 0 && unit.currentWaypoint < unit.path.length - 1) {
          unit.currentWaypoint++;
          unit.targetPosition = unit.path[unit.currentWaypoint];
        } else {
          unit.isMoving = false;
          unit.targetPosition = null;
          unit.path = [];
          unit.currentWaypoint = 0;
        }
      } else {
        // Move toward waypoint
        const moveX = (dx / distance) * speed;
        const moveZ = (dz / distance) * speed;

        unit.position.x += moveX;
        unit.position.z += moveZ;

        unit.rotation = Math.atan2(dx, dz);
      }

      this.updateUnitHeight(unit);
    }
  });
}
```

### Test the 3D pathfinding:

```javascript
// Test air unit movement with altitude changes
UnitSystem.moveUnit(testFighter, 15, 15, 10);  // Move to high altitude
UnitSystem.moveUnit(testVTOL, -15, -15, 2);    // Move to low altitude
```

### Implementation Steps

1. Add `findPath3D()` to PathfindingSystem
2. Add `heuristic3D()` helper function
3. Update `UnitSystem.moveUnit()` to handle air units
4. Update `UnitSystem.update()` to change altitude
5. Add test movements for air units
6. Save and test

### Acceptance Criteria

- [ ] 3D pathfinding function added
- [ ] Handles 26-directional movement
- [ ] Respects altitude min/max for unit types
- [ ] Air units move in 3D (X, Z, altitude)
- [ ] Fighter can move to high altitude (10)
- [ ] VTOL respects low altitude limit (1-5)
- [ ] Console shows "Found 3D path with N waypoints"

### Submit for Review

```
Task 2.3 complete! Implemented 3D pathfinding.

Added:
- findPath3D() with 26-directional search
- heuristic3D() for altitude distance
- Altitude validation per unit type
- Updated moveUnit() for air vs ground
- Updated unit.update() to handle altitude changes

Air units now:
- Path through 3D space
- Change altitude smoothly
- Respect min/max altitude limits

Ready for Task 2.4 (Air combat).
```

---

### TASK 2.4: Air Combat Mechanics (COMPLEX - Pro Agent)

### Goal
Implement air-to-air and air-to-ground combat with range and altitude restrictions.

### What to Add
Create a CombatSystem after AltitudeSystem:

### Code Template

```javascript
// ═══════════════════════════════════════════════════════
// COMBAT SYSTEM
// ═══════════════════════════════════════════════════════

console.log('Initializing combat system...');

const CombatSystem = {
  // Check if attacker can target defender
  canAttack(attacker, defender) {
    const attackerStats = UNIT_STATS[attacker.type];
    const defenderStats = UNIT_STATS[defender.type];

    // Calculate 2D distance
    const dx = defender.position.x - attacker.position.x;
    const dz = defender.position.z - attacker.position.z;
    const distance2D = Math.sqrt(dx * dx + dz * dz);

    // Check range
    if (distance2D > attackerStats.range) {
      return { canAttack: false, reason: 'out_of_range' };
    }

    // Altitude restrictions
    const altDiff = Math.abs((attacker.altitude || 0) - (defender.altitude || 0));

    // Air-to-air: Must be within 2 altitude levels
    if (attackerStats.type === 'air' && defenderStats.type === 'air') {
      if (altDiff > 2) {
        return { canAttack: false, reason: 'altitude_difference' };
      }
    }

    // Air-to-ground: Must be at altitude 1-4 to attack ground
    if (attackerStats.type === 'air' && defenderStats.type === 'ground') {
      const attackerAlt = attacker.altitude || 0;
      if (attackerAlt < 1 || attackerAlt > 4) {
        return { canAttack: false, reason: 'wrong_altitude' };
      }
    }

    // Ground-to-air: Limited range against aircraft
    if (attackerStats.type === 'ground' && defenderStats.type === 'air') {
      const defenderAlt = defender.altitude || 0;
      // Can only hit low-flying aircraft (altitude 1-3)
      if (defenderAlt > 3) {
        return { canAttack: false, reason: 'target_too_high' };
      }
    }

    return { canAttack: true };
  },

  // Perform attack
  attack(attacker, defender) {
    const canAttackResult = this.canAttack(attacker, defender);

    if (!canAttackResult.canAttack) {
      console.log(`${attacker.type} cannot attack: ${canAttackResult.reason}`);
      return false;
    }

    const attackerStats = UNIT_STATS[attacker.type];
    const damage = attackerStats.damage;

    // Apply damage
    defender.health -= damage;
    console.log(`${attacker.type} #${attacker.id} attacked ${defender.type} #${defender.id} for ${damage} damage`);
    console.log(`  ${defender.type} health: ${defender.health}/${defender.maxHealth}`);

    // Check if destroyed
    if (defender.health <= 0) {
      console.log(`💥 ${defender.type} #${defender.id} destroyed!`);
      this.destroyUnit(defender);
      return true;
    }

    return true;
  },

  // Destroy unit and remove from game
  destroyUnit(unit) {
    UnitSystem.removeUnit(unit);
  },

  // Find nearest enemy in range
  findTarget(attacker, enemyOwnerId) {
    let nearestEnemy = null;
    let nearestDistance = Infinity;

    for (const unit of UnitSystem.units) {
      if (unit.ownerId === enemyOwnerId && unit !== attacker) {
        const canAttackResult = this.canAttack(attacker, unit);

        if (canAttackResult.canAttack) {
          const dx = unit.position.x - attacker.position.x;
          const dz = unit.position.z - attacker.position.z;
          const distance = Math.sqrt(dx * dx + dz * dz);

          if (distance < nearestDistance) {
            nearestDistance = distance;
            nearestEnemy = unit;
          }
        }
      }
    }

    return nearestEnemy;
  }
};

console.log('✅ Combat system initialized');
```

### Add Auto-Attack to Unit Update Loop

Update `UnitSystem.update()` to check for targets:

```javascript
update(deltaTime) {
  this.units.forEach(unit => {
    // ... existing movement code ...

    // Auto-attack if not moving
    if (!unit.isMoving) {
      const stats = UNIT_STATS[unit.type];

      // Find enemy target (for testing, attack owner 1 if you're owner 0, etc.)
      const enemyOwnerId = (unit.ownerId + 1) % 2;  // Simple 2-player logic
      const target = CombatSystem.findTarget(unit, enemyOwnerId);

      if (target) {
        // Attack once per second (throttle with timer)
        if (!unit.lastAttackTime || Date.now() - unit.lastAttackTime > 1000) {
          CombatSystem.attack(unit, target);
          unit.lastAttackTime = Date.now();
        }
      }
    }
  });
}
```

### Implementation Steps

1. Add CombatSystem code
2. Implement canAttack() with altitude logic
3. Implement attack() with damage
4. Add destroyUnit() function
5. Update unit update loop for auto-attack
6. Test with existing units

### Acceptance Criteria

- [ ] CombatSystem added
- [ ] Air units can attack air targets (within 2 altitude levels)
- [ ] Air units can attack ground (altitude 1-4 only)
- [ ] Ground units can attack low aircraft (altitude 1-3)
- [ ] High-flying aircraft immune to ground fire
- [ ] Console shows damage and kills
- [ ] Destroyed units removed from scene

### Submit for Review

```
Task 2.4 complete! Implemented air combat system.

Added:
- CombatSystem with altitude-based restrictions
- canAttack() validation (range + altitude)
- attack() with damage and destruction
- findTarget() for auto-engagement
- Destroyed units properly removed

Combat rules:
- Air-to-air: ±2 altitude levels
- Air-to-ground: altitude 1-4 required
- Ground-to-air: max altitude 3 targets
- Auto-attack every 1 second

Ready for Task 2.5 (Visual feedback).
```

---

### TASK 2.5: Visual Feedback for Air Combat

### Goal
Add altitude indicators, shadows, and projectile effects for better gameplay feedback.

### What to Add

**Step 1: Add altitude indicator rings to air units**

Update `UnitSystem.createUnit()` to add indicator:

```javascript
createUnit(type, x, z, ownerId) {
  // ... existing code ...

  const unit = {
    // ... existing fields ...
    altitudeIndicator: null  // NEW
  };

  // ... create mesh ...

  // NEW: Add altitude indicator for air units
  const stats = UNIT_STATS[type];
  if (stats.type === 'air') {
    const indicatorGeometry = new THREE.RingGeometry(0.8, 1.0, 16);
    const indicatorMaterial = new THREE.MeshBasicMaterial({
      color: PLAYER_COLORS[ownerId],
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.3
    });
    unit.altitudeIndicator = new THREE.Mesh(indicatorGeometry, indicatorMaterial);
    unit.altitudeIndicator.rotation.x = -Math.PI / 2;  // Lay flat
    scene.add(unit.altitudeIndicator);
  }

  // ... rest of function ...
}
```

**Step 2: Update altitude indicator position**

Update `UnitSystem.updateUnitHeight()`:

```javascript
updateUnitHeight(unit) {
  const terrainHeight = TerrainSystem.getHeightAt(unit.position.x, unit.position.z);

  const stats = UNIT_STATS[unit.type];
  const heightOffset = unit.type === 'ARTILLERY' ? 2.0 : 1.0;

  // Air units use altitude
  if (stats.type === 'air') {
    unit.position.y = AltitudeSystem.getYPosition(terrainHeight, unit.altitude || 0);
  } else {
    unit.position.y = terrainHeight + heightOffset;
  }

  // Update mesh
  unit.mesh.position.set(unit.position.x, unit.position.y, unit.position.z);
  unit.mesh.rotation.y = unit.rotation;

  // NEW: Update altitude indicator (shows on ground below aircraft)
  if (unit.altitudeIndicator) {
    unit.altitudeIndicator.position.set(
      unit.position.x,
      terrainHeight + 0.1,  // Just above terrain
      unit.position.z
    );
  }
}
```

**Step 3: Add projectile visual effect**

Add to CombatSystem.attack():

```javascript
attack(attacker, defender) {
  const canAttackResult = this.canAttack(attacker, defender);
  if (!canAttackResult.canAttack) return false;

  // NEW: Create projectile visual
  this.createProjectile(attacker, defender);

  // ... existing damage code ...
}
```

**Step 4: Implement projectile system:**

```javascript
// Add to CombatSystem
const CombatSystem = {
  projectiles: [],

  // ... existing methods ...

  createProjectile(from, to) {
    const geometry = new THREE.SphereGeometry(0.2, 8, 8);
    const material = new THREE.MeshBasicMaterial({ color: 0xff9900 });
    const projectile = new THREE.Mesh(geometry, material);

    projectile.position.set(from.position.x, from.position.y, from.position.z);
    scene.add(projectile);

    this.projectiles.push({
      mesh: projectile,
      startPos: { ...from.position },
      endPos: { ...to.position },
      progress: 0,
      speed: 15  // Units per second
    });
  },

  updateProjectiles(deltaTime) {
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      const proj = this.projectiles[i];
      proj.progress += proj.speed * deltaTime;

      if (proj.progress >= 1) {
        // Reached target - remove
        scene.remove(proj.mesh);
        this.projectiles.splice(i, 1);
      } else {
        // Interpolate position
        proj.mesh.position.x = proj.startPos.x + (proj.endPos.x - proj.startPos.x) * proj.progress;
        proj.mesh.position.y = proj.startPos.y + (proj.endPos.y - proj.startPos.y) * proj.progress;
        proj.mesh.position.z = proj.startPos.z + (proj.endPos.z - proj.startPos.z) * proj.progress;
      }
    }
  }
};
```

**Step 5: Update animation loop:**

```javascript
function animate() {
  animationFrameId = requestAnimationFrame(animate);

  const now = Date.now();
  const deltaTime = (now - lastTime) / 1000;
  lastTime = now;

  UnitSystem.update(deltaTime);
  CombatSystem.updateProjectiles(deltaTime);  // NEW

  renderer.render(scene, camera);
}
```

### Implementation Steps

1. Add altitude indicators to air units
2. Update indicator position on terrain
3. Add projectile creation to attacks
4. Implement projectile animation system
5. Update animation loop
6. Remove indicators when units destroyed

### Acceptance Criteria

- [ ] Air units show rings on ground below
- [ ] Rings match player color
- [ ] Projectiles spawn when attacking
- [ ] Projectiles travel from attacker to target
- [ ] Projectiles removed after hitting
- [ ] Everything updates smoothly

### Submit for Review

```
Task 2.5 complete! Added visual feedback for air combat.

Implemented:
- Altitude indicator rings (on terrain below aircraft)
- Projectile system with sphere geometry
- Smooth projectile interpolation
- Auto-cleanup after projectile hits

Visual improvements:
- Can see which altitude air units are at
- Combat is visible with projectiles
- Player colors match across units/indicators

✅ WEEK 2 COMPLETE!
All air unit and altitude features implemented.
Ready for Week 3 (Asset extraction & texturing).
```

---

## WEEK 2 COMPLETION CHECKPOINT

**Junior Developers:** Complete Tasks 2.1-2.5, then **STOP** and submit for review.

**Senior Architect (Claude Code) will:**
1. Review all air unit code
2. Test combat mechanics
3. Verify altitude restrictions
4. Approve before Week 3

---

## REMAINING TASKS (LOCKED)

- Task 3.1-3.5: Asset extraction and texturing (Week 3)
- Task 4.1-4.5: Multiplayer and federation (Week 4)

---

## Questions?

If you're stuck or confused:

1. **Re-read the onboarding guide** (`JUNIOR_DEV_ONBOARDING.md`)
2. **Check the reference applets** (hexgl.js, FortressOverlord.js)
3. **Read the error message carefully** (it usually tells you what's wrong)
4. **Ask your senior architect** (Claude Code) specific questions

---

**Good luck! Start with Task 0 and work your way through!**
