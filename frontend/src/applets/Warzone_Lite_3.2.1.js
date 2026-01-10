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
    const APPLET_VERSION = 'v3.2.1 - Fixed Textures & Ground Unit Visibility';

    // ═══════════════════════════════════════════════════════
    // Debug Console (enabled when BBS_DEBUG_MODE is set)
    // ═══════════════════════════════════════════════════════

    function debugLog(msg) {
      if (!window.BBS_DEBUG_MODE) return;
      const ts = new Date().toISOString().split('T')[1].slice(0, -1);
      const log = '[WZ ' + ts + '] ' + msg;
      console.log(log);
      const panel = document.getElementById('debug-panel');
      if (panel) {
        const e = document.createElement('div');
        e.textContent = log;
        e.style.cssText = 'font-size:0.7rem;color:#32cd32;margin:2px 0;font-family:monospace;';
        panel.appendChild(e);
        panel.scrollTop = panel.scrollHeight;
      }
    }

    // Create debug panel if debug mode is enabled
    if (window.BBS_DEBUG_MODE) {
      const dp = document.createElement('div');
      dp.id = 'debug-panel';
      dp.style.cssText = 'position:fixed;bottom:0;right:0;width:400px;max-height:200px;background:rgba(0,0,0,0.9);border:1px solid #32cd32;overflow-y:auto;padding:10px;z-index:9999;font-size:0.7rem;color:#32cd32;font-family:monospace;';
      document.body.appendChild(dp);

      // Show version prominently at top
      const versionDiv = document.createElement('div');
      versionDiv.textContent = '=== WARZONE LITE ' + APPLET_VERSION + ' ===';
      versionDiv.style.cssText = 'font-size:0.8rem;color:#ffff00;font-weight:bold;margin-bottom:5px;border-bottom:1px solid #32cd32;padding-bottom:3px;';
      dp.appendChild(versionDiv);
    }

    console.log('═══════════════════════════════════════════════════');
    console.log(`🎮 Warzone Lite ${APPLET_VERSION}`);
    console.log('═══════════════════════════════════════════════════');
    debugLog('Starting applet...');

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

    debugLog('Loading Three.js...');
    await loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js');

    if (!window.THREE) {
      throw new Error('Three.js failed to load');
    }

    debugLog('✅ Three.js loaded successfully');

    // Load Yuka.js for AI behaviors
    debugLog('Loading Yuka.js AI library...');
    await loadScript('https://cdn.jsdelivr.net/npm/yuka@latest/build/yuka.min.js');

    if (!window.YUKA) {
      throw new Error('Yuka.js failed to load');
    }

    debugLog('✅ Yuka.js AI library loaded');

    // ═══════════════════════════════════════════════════════
    // STEP 1.5: Load Warzone 2100 Texture Atlas
    // ═══════════════════════════════════════════════════════

    // ═══════════════════════════════════════════════════════
    // PIE Model Loader (Warzone 2100 Format)
    // ═══════════════════════════════════════════════════════

    function parsePIE(pieText) {
      const lines = pieText.split('\n').map(l => l.trim()).filter(l => l && !l.startsWith('#'));
      let version = 2;
      let textureSize = 256;
      const points = [];
      const polygons = [];
      const connectors = [];

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const parts = line.split(/\s+/);

        if (parts[0] === 'PIE') {
          version = parseInt(parts[1]);
        } else if (parts[0] === 'TEXTURE' && parts.length >= 4) {
          textureSize = parseInt(parts[3]);
        } else if (parts[0] === 'POINTS') {
          const numPoints = parseInt(parts[1]);
          for (let j = 0; j < numPoints && i + j + 1 < lines.length; j++) {
            const pointLine = lines[i + j + 1].split(/\s+/);
            if (pointLine.length >= 3) {
              points.push([
                parseFloat(pointLine[0]),
                parseFloat(pointLine[1]),
                parseFloat(pointLine[2])
              ]);
            }
          }
          i += numPoints;
        } else if (parts[0] === 'POLYGONS') {
          const numPolygons = parseInt(parts[1]);
          for (let j = 0; j < numPolygons && i + j + 1 < lines.length; j++) {
            const polyLine = lines[i + j + 1].split(/\s+/);
            if (polyLine.length >= 10) {
              const vertCount = parseInt(polyLine[1]);
              const indices = [];
              const uvs = [];

              for (let k = 0; k < vertCount; k++) {
                indices.push(parseInt(polyLine[2 + k]));
              }

              for (let k = 0; k < vertCount; k++) {
                const uvStart = 2 + vertCount + k * 2;
                uvs.push([
                  parseFloat(polyLine[uvStart]) / textureSize,
                  1.0 - (parseFloat(polyLine[uvStart + 1]) / textureSize)
                ]);
              }

              polygons.push({ indices, uvs });
            }
          }
          i += numPolygons;
        } else if (parts[0] === 'CONNECTORS') {
          const numConnectors = parseInt(parts[1]);
          for (let j = 0; j < numConnectors && i + j + 1 < lines.length; j++) {
            const connLine = lines[i + j + 1].split(/\s+/);
            if (connLine.length >= 3) {
              // Connector format: x z y (note: z and y are swapped in connector coordinates)
              connectors.push([
                parseFloat(connLine[0]),
                parseFloat(connLine[1]),
                parseFloat(connLine[2])
              ]);
            }
          }
          i += numConnectors;
        }
      }

      return { points, polygons, connectors };
    }

    async function loadPIEModel(url) {
      const response = await fetch(url);
      const pieText = await response.text();
      return parsePIE(pieText);
    }

    function createGeometryFromPIE(pieData) {
      const geometry = new THREE.BufferGeometry();
      const vertices = [];
      const uvs = [];
      const indices = [];

      let vertexIndex = 0;
      for (const poly of pieData.polygons) {
        for (let i = 0; i < poly.indices.length; i++) {
          const pointIdx = poly.indices[i];
          const point = pieData.points[pointIdx];
          vertices.push(point[0] / 128, point[1] / 128, point[2] / 128);
          uvs.push(poly.uvs[i][0], poly.uvs[i][1]);
        }

        if (poly.indices.length === 3) {
          indices.push(vertexIndex, vertexIndex + 1, vertexIndex + 2);
          vertexIndex += 3;
        } else if (poly.indices.length === 4) {
          indices.push(vertexIndex, vertexIndex + 1, vertexIndex + 2);
          indices.push(vertexIndex, vertexIndex + 2, vertexIndex + 3);
          vertexIndex += 4;
        }
      }

      geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
      geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      geometry.setIndex(indices);
      geometry.computeVertexNormals();

      return geometry;
    }

    debugLog('Loading Warzone 2100 assets...');

    const textureLoader = new THREE.TextureLoader();
    let textures = {
      bodies: null,
      propulsion: null,
      weapons: null,
      air: null
    };
    let pieModels = {
      bodies: {},
      propulsion: {},
      weapons: {}
    };

    // Helper function to load texture
    function loadTexture(url) {
      return new Promise((resolve) => {
            textureLoader.load(
              url,
              (texture) => {
                texture.wrapS = THREE.ClampToEdgeWrapping;
                texture.wrapT = THREE.ClampToEdgeWrapping;
                texture.minFilter = THREE.LinearFilter;
                texture.magFilter = THREE.LinearFilter;
                texture.colorSpace = THREE.SRGBColorSpace;  // Proper color space for textures
                texture.needsUpdate = true;  // Force GPU upload
                debugLog('  Loaded: ' + url.split('/').pop());
                resolve(texture);
              },
              undefined,
              (err) => {
                console.warn('Texture load failed:', url, err);
                debugLog(`❌ ERROR: Texture load failed: ${url}`); // Added for visibility
                resolve(null);
              }
            );      });
    }

    // Load textures and PIE models in parallel
    await Promise.all([
      // Load texture atlases
      (async () => {
        textures.bodies = await loadTexture('/static/warzone_textures/page-14-droid-hubs.png');
        textures.propulsion = await loadTexture('/static/warzone_textures/page-16-droid-drives.png');
        textures.weapons = await loadTexture('/static/warzone_textures/page-17-droid-weapons.png');
        textures.air = await loadTexture('/static/warzone_textures/page-200-air-units.png');
      })(),
      // Load body PIE models
      (async () => {
        try {
          pieModels.bodies.SCOUT = await loadPIEModel('/warzone_models/body_light.pie');
          pieModels.bodies.TANK = await loadPIEModel('/warzone_models/body_medium.pie');
          pieModels.bodies.ARTILLERY = await loadPIEModel('/warzone_models/body_heavy.pie');
        } catch (err) {
          console.warn('Body PIE model load failed:', err);
        }
      })(),
      // Load propulsion PIE models
      (async () => {
        try {
          pieModels.propulsion.SCOUT = await loadPIEModel('/warzone_models/prop_tracks_light.pie');
          pieModels.propulsion.TANK = await loadPIEModel('/warzone_models/prop_tracks_medium.pie');
          pieModels.propulsion.ARTILLERY = await loadPIEModel('/warzone_models/prop_tracks_heavy.pie');
        } catch (err) {
          console.warn('Propulsion PIE model load failed:', err);
        }
      })(),
      // Load weapon PIE models
      (async () => {
        try {
          pieModels.weapons.SCOUT = await loadPIEModel('/warzone_models/weapon_cannon.pie');
          pieModels.weapons.TANK = await loadPIEModel('/warzone_models/weapon_cannon.pie');
          pieModels.weapons.ARTILLERY = await loadPIEModel('/warzone_models/weapon_mortar.pie');
        } catch (err) {
          console.warn('Weapon PIE model load failed:', err);
        }
      })()
    ]);

    const textureCount = (textures.bodies ? 1 : 0) + (textures.propulsion ? 1 : 0) + (textures.weapons ? 1 : 0);
    debugLog(textureCount === 3 ? '✅ Textures loaded (3)' : `⚠️  Textures partial (${textureCount}/3)`);
    debugLog('  Bodies: ' + (textures.bodies ? 'OK' : 'FAIL'));
    debugLog('  Propulsion: ' + (textures.propulsion ? 'OK' : 'FAIL'));
    debugLog('  Weapons: ' + (textures.weapons ? 'OK' : 'FAIL'));
    const modelCount = Object.keys(pieModels.bodies).length + Object.keys(pieModels.propulsion).length + Object.keys(pieModels.weapons).length;
    debugLog(modelCount === 9 ? '✅ PIE models loaded (9)' : `⚠️  PIE models partial (${modelCount}/9)`);

    // ═══════════════════════════════════════════════════════
    // STEP 2: Get User and Applet Info
    // ═══════════════════════════════════════════════════════

    const userInfo = await window.bbs.getUserInfo();
    const appletInfo = await window.bbs.getAppletInfo();

    debugLog('User: ' + userInfo.nickname);
    debugLog('Applet ID: ' + appletInfo.id);

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
    mountPoint.tabIndex = 0;  // Allow keyboard focus
    mountPoint.style.outline = 'none';  // Remove focus outline for cleaner look
    appletContainer.appendChild(mountPoint);
    mountPoint.focus();  // Auto-focus for immediate keyboard control

    debugLog('✅ Container initialized');

    // ═══════════════════════════════════════════════════════
    // STEP 4: Three.js Scene Setup
    // ═══════════════════════════════════════════════════════

    debugLog('Setting up Three.js scene...');

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a2e40);
    scene.fog = new THREE.Fog(0x1a2e40, 50, 150);

    // Camera (Orthographic for RTS view with zoom/pan controls)
    const aspect = window.innerWidth / window.innerHeight;
    let viewSize = 20;  // Start more zoomed in (was 40)
    const camera = new THREE.OrthographicCamera(
      -viewSize * aspect,
      viewSize * aspect,
      viewSize,
      -viewSize,
      1,
      1000
    );

    // Camera control state
    const cameraTarget = new THREE.Vector3(0, 0, 0);
    const cameraOffset = new THREE.Vector3(30, 40, 30);

    function updateCamera() {
      camera.position.copy(cameraTarget).add(cameraOffset);
      camera.lookAt(cameraTarget);

      // Update orthographic frustum for zoom
      const aspect = window.innerWidth / window.innerHeight;
      camera.left = -viewSize * aspect;
      camera.right = viewSize * aspect;
      camera.top = viewSize;
      camera.bottom = -viewSize;
      camera.updateProjectionMatrix();
    }

    updateCamera();

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

    debugLog('✅ Three.js scene setup complete');

    // ═══════════════════════════════════════════════════════
    // STEP 5: Create Test Geometry
    // ═══════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════
// STEP 5: Terrain System
// ═══════════════════════════════════════════════════════

debugLog('Generating terrain...');

const TerrainSystem = {
  size: { width: 64, depth: 80 },
  heightLevels: 8,
  heightMap: null,
  roadMap: null,
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
    this.roadMap = []; // Initialize road map
    const noise = this.generatePerlinNoise(this.size.width, this.size.depth, 32);
    const ruggedNoise = this.generatePerlinNoise(this.size.width, this.size.depth, 12);

    for (let z = 0; z < this.size.depth; z++) {
      map[z] = [];
      this.roadMap[z] = [];
      for (let x = 0; x < this.size.width; x++) {
        this.roadMap[z][x] = 0; // Default to no road
        let height = 1;

        const mountainGradient = z / this.size.depth;
        if (mountainGradient > 0.3) {
            const gradientProgress = (mountainGradient - 0.3) / 0.7;
            height += Math.floor(noise[z][x] * 4 * gradientProgress);
            height += Math.floor(ruggedNoise[z][x] * 2 * gradientProgress);
        }

        if (x > this.size.width - 20 && z > this.size.depth - 20) {
            height = Math.max(height, 5);
        }
        if (x < 15 && z < 15) {
            height = 1;
        }

        const riverX = this.size.width / 2.5 + Math.sin(z / 6) * 8;
        if (x > riverX - 1.5 && x < riverX + 1.5) {
            height = 0;
        }

        map[z][x] = Math.max(0, Math.min(this.heightLevels, height));
      }
    }

    // Add roads and bridges after heights are set
    const roadZ1 = Math.floor(this.size.depth * 0.3);
    const roadZ2 = Math.floor(this.size.depth * 0.7);
    for (let x = 0; x < this.size.width; x++) {
        // Horizontal roads
        this.roadMap[roadZ1][x] = 1;
        this.roadMap[roadZ2][x] = 1;
        // Ensure road is on solid ground
        if (map[roadZ1][x] < 1) map[roadZ1][x] = 1;
        if (map[roadZ2][x] < 1) map[roadZ2][x] = 1;
    }
    // Add bridges where roads cross the river
    for (let z = 0; z < this.size.depth; z++) {
        if (this.roadMap[z][Math.floor(this.size.width / 2.5)]) {
             const riverX = this.size.width / 2.5 + Math.sin(z / 6) * 8;
             for (let x_br = Math.floor(riverX - 1.5); x_br < riverX + 1.5; x_br++) {
                 if (map[z][x_br] === 0) map[z][x_br] = 1; // Place bridge
             }
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

    // Apply heights and vertex colors
    const positions = geometry.attributes.position;
    const colors = [];
    const color = new THREE.Color();

    for (let i = 0; i < positions.count; i++) {
      const x = Math.floor(i % this.size.width);
      const z = Math.floor(i / this.size.width);
      const height = this.heightMap[z] ? this.heightMap[z][x] : 0;

      // Y is "up" in Three.js
      positions.setY(i, height);

      // Set vertex color based on height for a desert/mountain theme
      if (TerrainSystem.roadMap[z][x] === 1) {
        color.set(0x444444); // Dark grey for roads
      } else if (height < 1) {
        color.set(0x336699); // Water
      } else if (height < 2) {
        color.set(0xC2B280); // Sandy Desert/Beach
      } else if (height < 4) {
        // Mix of green and brown for foothills
        const t = (height - 2) / 2;
        color.set(0x6B8E23).lerp(new THREE.Color(0x967969), t);
      } else {
        // Mix of green, grey, and white for mountains
        const t = Math.min(1, (height - 4) / 4);
        color.set(0x677862).lerp(new THREE.Color(0xcccccc), t); // Start with a grey-green
      }
      colors.push(color.r, color.g, color.b);
    }

    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

    // Recompute normals for lighting
    geometry.computeVertexNormals();

    // Create material that uses vertex colors
    const material = new THREE.MeshStandardMaterial({
      roughness: 0.9, // More rough for natural terrain
      metalness: 0.1,
      vertexColors: true // Enable vertex colors
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
  },

  // Get terrain normal at world position by sampling height
  getNormalAt(x, z) {
    const d = 0.5; // Distance to sample for slope calculation
    const hx_plus = this.getHeightAt(x + d, z);
    const hx_minus = this.getHeightAt(x - d, z);
    const hz_plus = this.getHeightAt(x, z + d);
    const hz_minus = this.getHeightAt(x, z - d);

    // Calculate slope in X and Z directions
    const slopeX = (hx_plus - hx_minus) / (2 * d);
    const slopeZ = (hz_plus - hz_minus) / (2 * d);

    // Create normal vector from slopes and normalize it
    const normal = new THREE.Vector3(-slopeX, 1, -slopeZ).normalize();
    return normal;
  }
};

// Generate and add terrain to scene
const terrain = TerrainSystem.generate();
scene.add(terrain);

debugLog('✅ Terrain generated with ' +
  (TerrainSystem.size.width * TerrainSystem.size.depth) + ' vertices ' +
  '(' + TerrainSystem.size.width + 'x' + TerrainSystem.size.depth + ')');

// ═══════════════════════════════════════════════════════
// Yuka AI System
// ═══════════════════════════════════════════════════════

const yukaEntityManager = new YUKA.EntityManager();
const yukaTime = new YUKA.Time();

debugLog('✅ Yuka.js Entity Manager initialized');

// ═══════════════════════════════════════════════════════
// UNIT SYSTEM
// ═══════════════════════════════════════════════════════

debugLog('Initializing unit system...');

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
  },

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
    defaultAltitude: 5
  },
  BOMBER: {
    cost: 400,
    health: 90,
    damage: 40,
    range: 6,
    speed: 2,
    type: 'air',
    defaultAltitude: 7
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
      altitude: 0,  // NEW: Track altitude level
      mesh: null,
      hitbox: null,  // Invisible larger collision box for easier selection
      selectionRing: null,  // Visual selection indicator
      altitudeIndicator: null, // NEW
      path: [],  // Array of waypoints
      currentWaypoint: 0,
      targetPosition: null,
      isMoving: false
    };

    // Create 3D mesh
    unit.mesh = this.createMesh(type, ownerId, stats);

    // Create invisible hitbox for easier selection
    unit.hitbox = this.createHitbox(type);
    unit.hitbox.userData.unitId = unit.id;  // Link hitbox to unit

    // Create selection ring with player color
    unit.selectionRing = this.createSelectionRing(ownerId);

    // NEW: Add altitude indicator for air units
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

    // Position on terrain
    this.updateUnitHeight(unit);

    // NEW: Set altitude for air units
    if (stats.type === 'air' && stats.defaultAltitude) {
      AltitudeSystem.setAltitude(unit, stats.defaultAltitude);
    }

    // Create Yuka vehicle for AI movement
    const vehicle = new YUKA.Vehicle();
    vehicle.position.set(unit.position.x, unit.position.y, unit.position.z);
    vehicle.maxSpeed = stats.speed;
    vehicle.maxForce = 5; // Steering force
    vehicle.updateOrientation = false; // We handle rotation separately

    // Add obstacle avoidance (units avoid each other)
    const avoidBehavior = new YUKA.ObstacleAvoidanceBehavior([], 3);
    vehicle.steering.add(avoidBehavior);

    // Store reference
    unit.yukaVehicle = vehicle;
    yukaEntityManager.add(vehicle);

    // Add to scene and tracking array
    scene.add(unit.mesh);
    scene.add(unit.hitbox);
    scene.add(unit.selectionRing);
    this.units.push(unit);

    debugLog('Created ' + type + ' unit #' + unit.id + ' for player ' + ownerId + ' at (' + x.toFixed(1) + ', ' + z.toFixed(1) + ') with Yuka vehicle');

    return unit;
  },

  // Create 3D mesh for unit using PIE models (assembles body + propulsion + weapon)
  createMesh(type, ownerId, stats) {
    const droidGroup = new THREE.Group();
    droidGroup.userData = { unitId: null };

    // Check if we have PIE models for this type
    const hasBody = pieModels.bodies[type];
    const hasProp = pieModels.propulsion[type];
    const hasWeapon = pieModels.weapons[type];

    if (hasBody && hasProp && hasWeapon) {
      // COMPONENT ASSEMBLY: Build droid from body + propulsion + weapon

      // 1. Create PROPULSION meshes (WZ2100 tracks are modeled for one side only - need to mirror)
      // Create FRESH geometry for each track (don't clone - cloning may not copy attributes properly)

      // Right track (original)
      const propMaterialRight = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        emissive: 0x000000,
        specular: 0x444444,
        shininess: 20,
        side: THREE.DoubleSide // Render both sides to fix mirroring issue
      });
      if (textures.propulsion) {
        propMaterialRight.map = textures.propulsion;  // Shared texture (no clone)
        propMaterialRight.needsUpdate = true;
      }
      const propGeometryRight = createGeometryFromPIE(pieModels.propulsion[type]);
      const propMeshRight = new THREE.Mesh(propGeometryRight, propMaterialRight);
      propMeshRight.castShadow = true;
      propMeshRight.receiveShadow = true;
      propMeshRight.position.set(0, 0, 0);
      droidGroup.add(propMeshRight);

      // Left track (mirrored copy) - create FRESH geometry, don't clone
      const propMaterialLeft = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        emissive: 0x000000,
        specular: 0x444444,
        shininess: 20,
        side: THREE.DoubleSide // Render both sides to fix mirroring issue
      });
      if (textures.propulsion) {
        propMaterialLeft.map = textures.propulsion;  // Shared texture (no clone)
        propMaterialLeft.needsUpdate = true;
      }
      const propGeometryLeft = createGeometryFromPIE(pieModels.propulsion[type]);
      const propMeshLeft = new THREE.Mesh(propGeometryLeft, propMaterialLeft);
      propMeshLeft.castShadow = true;
      propMeshLeft.receiveShadow = true;
      propMeshLeft.position.set(0, 0, 0);
      propMeshLeft.scale.x = -1;  // Mirror along X axis for left side
      droidGroup.add(propMeshLeft);

      // 2. Create BODY mesh (sitting on top of propulsion)
      const bodyGeometry = createGeometryFromPIE(pieModels.bodies[type]);
      const bodyMaterial = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        emissive: 0x000000,
        specular: 0x444444,
        shininess: 20
      });
      if (textures.bodies) {
        bodyMaterial.map = textures.bodies;
        bodyMaterial.needsUpdate = true;
      }
      const bodyMesh = new THREE.Mesh(bodyGeometry, bodyMaterial);
      bodyMesh.castShadow = true;
      bodyMesh.receiveShadow = true;
      // Position body above propulsion (WZ2100 droids have body on top of tracks)
      bodyMesh.position.set(0, 0.2, 0);  // Raised to sit on tracks
      droidGroup.add(bodyMesh);

      // 3. Create WEAPON/TURRET mesh (positioned using body connector #0)
      const weaponGeometry = createGeometryFromPIE(pieModels.weapons[type]);
      const weaponMaterial = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        emissive: 0x000000,
        specular: 0x444444,
        shininess: 20
      });
      if (textures.weapons) {
        weaponMaterial.map = textures.weapons;
        weaponMaterial.needsUpdate = true;
      }
      const weaponMesh = new THREE.Mesh(weaponGeometry, weaponMaterial);
      weaponMesh.castShadow = true;
      weaponMesh.receiveShadow = true;

      // Rotate turret 180° to face forward (WZ2100 PIE models face backwards by default)
      weaponMesh.rotation.y = Math.PI;

      // Position weapon using connector #0 from body (turret mount point)
      // Connector format from PIE: x z y (z is up in PIE connector coordinates)
      if (pieModels.bodies[type].connectors && pieModels.bodies[type].connectors.length > 0) {
        const conn = pieModels.bodies[type].connectors[0];
        // Convert PIE connector coords (x, z, y) to Three.js (x, y, z) with scaling
        // Add body Y offset since weapon is relative to body
        weaponMesh.position.set(
          conn[0] / 128,
          conn[2] / 128 + 0.2,  // Add body height offset
          conn[1] / 128
        );
      } else {
        // Fallback position if no connector
        weaponMesh.position.set(0, 0.5, 0);  // Adjusted for body height
      }
      droidGroup.add(weaponMesh);

      // Scale entire droid assembly for visibility
      droidGroup.scale.set(1.5, 1.5, 1.5);

    } else {
      // FALLBACK: Use primitive geometry if PIE models didn't load
      let geometry;
      // NOTE: These are fallback dimensions, adjusted to be more consistent with PIE model sizes.
      switch (type) {
        case 'TANK':
          geometry = new THREE.BoxGeometry(1.2, 0.8, 1.8);
          break;
        case 'ARTILLERY':
          geometry = new THREE.CylinderGeometry(0.8, 1, 1.5, 8);
          break;
        case 'SCOUT':
          geometry = new THREE.BoxGeometry(0.8, 0.5, 1.2);
          break;

        case 'VTOL':
          // Diamond/wedge shape for VTOL
          geometry = new THREE.ConeGeometry(0.5, 1.5, 4);
          geometry.rotateX(Math.PI / 2);  // Point forward
          break;

        case 'FIGHTER':
          // Sleek arrow shape for fighter
          geometry = new THREE.ConeGeometry(0.4, 2.0, 3);
          geometry.rotateX(Math.PI / 2);  // Point forward
          break;

        case 'BOMBER':
          // Wide box for bomber
          geometry = new THREE.BoxGeometry(1.8, 0.4, 1.5);
          break;
        default:
          geometry = new THREE.BoxGeometry(1, 1, 1);
      }

      // Create material with player colors (no textures for simple geometry)
      const material = new THREE.MeshPhongMaterial({
        color: PLAYER_COLORS[ownerId],
        emissive: 0x222222,
        specular: 0x444444,
        shininess: 30
      });

      // For air units, apply the specific air texture if available
      if (stats.type === 'air' && textures.air) {
        material.map = textures.air;
        material.color.set(0xffffff); // Use white color to show texture correctly
        material.needsUpdate = true;
      }

      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.scale.set(1.5, 1.5, 1.5);
      droidGroup.add(mesh);
    }

    return droidGroup;
  },

  // Create invisible larger hitbox for easier selection
  createHitbox(type) {
    let geometry;

    switch (type) {
      case 'TANK':
        geometry = new THREE.BoxGeometry(5, 3, 6);  // Larger than visible mesh
        break;
      case 'ARTILLERY':
        geometry = new THREE.CylinderGeometry(3, 3, 5, 8);  // Much larger for easier clicking
        break;
      case 'SCOUT':
        geometry = new THREE.BoxGeometry(4, 2, 5);
        break;
      default:
        geometry = new THREE.BoxGeometry(4, 4, 4);
    }

    const material = new THREE.MeshBasicMaterial({
      transparent: true,
      opacity: 0,  // Completely invisible
      visible: true
    });

    const hitbox = new THREE.Mesh(geometry, material);
    hitbox.userData = { isHitbox: true };

    return hitbox;
  },

  // Create selection ring indicator with player color
  createSelectionRing(ownerId = 0) {
    const geometry = new THREE.RingGeometry(2, 2.5, 32);
    const material = new THREE.MeshBasicMaterial({
      color: PLAYER_COLORS[ownerId],  // Use player color for team identification
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.8
    });
    const ring = new THREE.Mesh(geometry, material);
    ring.rotation.x = -Math.PI / 2;  // Lay flat on ground
    ring.visible = false;  // Hidden by default
    return ring;
  },

  // Update unit's Y position to match terrain
  updateUnitHeight(unit) {
    const terrainHeight = TerrainSystem.getHeightAt(
      unit.position.x,
      unit.position.z
    );

    const stats = UNIT_STATS[unit.type];
    const heightOffset = unit.type === 'ARTILLERY' ? 2.0 : 1.0;

    // Air units use altitude
    if (stats.type === 'air') {
      unit.position.y = AltitudeSystem.getYPosition(terrainHeight, unit.altitude || 0);
    } else {
      unit.position.y = terrainHeight + heightOffset;
    }

    // Update mesh position
    unit.mesh.position.set(
      unit.position.x,
      unit.position.y,
      unit.position.z
    );

    unit.mesh.rotation.y = unit.rotation;

    // Update hitbox position (same as mesh)
    if (unit.hitbox) {
      unit.hitbox.position.set(
        unit.position.x,
        unit.position.y,
        unit.position.z
      );
      unit.hitbox.rotation.y = unit.rotation;
    }

    // Update selection ring position (on ground, above terrain to prevent z-fighting)
    if (unit.selectionRing) {
      unit.selectionRing.position.set(
        unit.position.x,
        terrainHeight + 0.2,  // Increased from 0.1 to prevent z-fighting
        unit.position.z
      );
    }

    // NEW: Update altitude indicator (shows on ground below aircraft)
    if (unit.altitudeIndicator) {
      unit.altitudeIndicator.position.set(
        unit.position.x,
        terrainHeight + 0.1,  // Just above terrain
        unit.position.z
      );
    }
  },

  // Move unit toward target using Yuka steering behaviors
  moveUnit(unit, targetX, targetZ, targetAlt) {
    const stats = UNIT_STATS[unit.type];

    // Clear previous steering behaviors
    unit.yukaVehicle.steering.clear();

    // Re-add obstacle avoidance (always active)
    const allObstacles = UnitSystem.units
      .filter(u => u !== unit && u.yukaVehicle)
      .map(u => u.yukaVehicle);
    const avoidBehavior = new YUKA.ObstacleAvoidanceBehavior(allObstacles, 3);
    unit.yukaVehicle.steering.add(avoidBehavior);

    // Ground units use A* pathfinding + Yuka FollowPath
    if (stats.type === 'ground') {
      debugLog(`Finding path for ground unit ${unit.id}...`);
      const path = PathfindingSystem.findPath(unit.position.x, unit.position.z, targetX, targetZ);

      if (path && path.length > 0) {
        const yukaPath = new YUKA.Path();
        path.forEach(waypoint => {
          // The Y position will be determined by the terrain height at the waypoint
          const terrainHeight = TerrainSystem.getHeightAt(waypoint.x, waypoint.z);
          const heightOffset = unit.type === 'ARTILLERY' ? 2.0 : 1.0;
          yukaPath.add(new YUKA.Vector3(waypoint.x, terrainHeight + heightOffset, waypoint.z));
        });

        yukaPath.loop = false; // Don't loop the path

        const followPathBehavior = new YUKA.FollowPathBehavior(yukaPath, 1.5); // 1.5 radius to consider waypoint reached
        unit.yukaVehicle.steering.add(followPathBehavior);

        unit.isMoving = true;
        unit.targetPosition = { x: targetX, z: targetZ }; // Still store final destination

        debugLog(`Unit ${unit.id} (${unit.type}) following path with ${path.length} waypoints via Yuka FollowPathBehavior`);
      } else {
        debugLog(`No path found for unit ${unit.id}.`);
        unit.isMoving = false;
        unit.targetPosition = null;
        unit.yukaVehicle.velocity.set(0, 0, 0); // Stop the vehicle
      }
    }
    // Air units use Arrive behavior, but only in the XZ plane. Altitude is handled in the animate() loop.
    else if (stats.type === 'air') {
      const finalTargetAlt = targetAlt !== undefined ? targetAlt : unit.altitude;
      unit.targetAltitude = finalTargetAlt;

      // Target the destination in XZ, but use the vehicle's current Y.
      // The animate loop will smoothly adjust Y to the target altitude.
      const targetPosition = new YUKA.Vector3(targetX, unit.yukaVehicle.position.y, targetZ);
      const arriveBehavior = new YUKA.ArriveBehavior(targetPosition, 2, 0.5);
      unit.yukaVehicle.steering.add(arriveBehavior);

      unit.isMoving = true;
      unit.targetPosition = { x: targetX, z: targetZ };

      debugLog(`Air unit ${unit.id} (${unit.type}) moving to (${targetX.toFixed(1)}, ${targetZ.toFixed(1)}). Target altitude: ${finalTargetAlt}`);
    }
  },

  // Update all units (called every frame)
  update(deltaTime) {
    this.units.forEach(unit => {
      // Check if unit has arrived at target (Yuka handles movement)
      if (unit.isMoving && unit.targetPosition) {
        const dx = unit.targetPosition.x - unit.position.x;
        const dz = unit.targetPosition.z - unit.position.z;
        const distance = Math.sqrt(dx * dx + dz * dz);

        // Check if arrived (within 1 unit of target)
        if (distance < 1.0) {
          unit.isMoving = false;
          unit.targetPosition = null;

          // Stop the Yuka vehicle
          unit.yukaVehicle.velocity.set(0, 0, 0);

          debugLog(`Unit ${unit.id} arrived at destination`);
        }
      }

      // Auto-attack if not moving
      if (!unit.isMoving) {
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
  },

  // Get unit by ID
  getUnitById(id) {
    return this.units.find(u => u.id === id);
  },

  // Remove unit
  removeUnit(unit) {
    scene.remove(unit.mesh);
    if (unit.hitbox) scene.remove(unit.hitbox);
    if (unit.selectionRing) scene.remove(unit.selectionRing);
    if (unit.altitudeIndicator) scene.remove(unit.altitudeIndicator);
    const index = this.units.indexOf(unit);
    if (index > -1) {
      this.units.splice(index, 1);
    }
  }
};

// ═══════════════════════════════════════════════════════
// ALTITUDE SYSTEM (For Air Units)
// ═══════════════════════════════════════════════════════

debugLog('Initializing altitude system...');

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

    debugLog(`${unit.type} #${unit.id} altitude set to ${unit.altitude}`);
  }
};

debugLog('✅ Altitude system initialized');
debugLog('   Altitude levels: 0 (ground) to 10 (high)');
debugLog('   Level height: 2 units');

// Create test units
const testTank = UnitSystem.createUnit('TANK', -10, -10, 0);
const testArtillery = UnitSystem.createUnit('ARTILLERY', 10, -10, 1);
const testScout = UnitSystem.createUnit('SCOUT', 0, 10, 0);

// Create test air units
const testVTOL = UnitSystem.createUnit('VTOL', -5, 5, 0);
const testFighter = UnitSystem.createUnit('FIGHTER', 5, 5, 1);
const testBomber = UnitSystem.createUnit('BOMBER', 0, -5, 2);

debugLog('✅ Unit system initialized with ' + UnitSystem.units.length + ' units (ground + air)');

// ═══════════════════════════════════════════════════════
// COMBAT SYSTEM
// ═══════════════════════════════════════════════════════

console.log('Initializing combat system...');

const CombatSystem = {
  projectiles: [],

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

    // NEW: Create projectile visual
    this.createProjectile(attacker, defender);

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
  },

  // Destroy unit and remove from game
  destroyUnit(unit) {
    debugLog(`💥 Unit ${unit.id} (${unit.type}) destroyed by enemy action.`);
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

// ═══════════════════════════════════════════════════════
// A* PATHFINDING SYSTEM
// ═══════════════════════════════════════════════════════

debugLog('Initializing pathfinding system...');

const PathfindingSystem = {
  // Convert world coordinates to grid coordinates
  worldToGrid(x, z) {
    const gridX = Math.floor(x + TerrainSystem.size.width / 2);
    const gridZ = Math.floor(z + TerrainSystem.size.depth / 2);
    return { x: gridX, z: gridZ };
  },

  // Convert grid coordinates to world coordinates
  gridToWorld(gridX, gridZ) {
    const x = gridX - TerrainSystem.size.width / 2;
    const z = gridZ - TerrainSystem.size.depth / 2;
    return { x, z };
  },

  // Check if grid position is valid
  isValidPosition(gridX, gridZ) {
    return gridX >= 0 && gridX < TerrainSystem.size.width &&
           gridZ >= 0 && gridZ < TerrainSystem.size.depth;
  },

  // Calculate movement cost between two grid positions
  getMovementCost(fromX, fromZ, toX, toZ) {
    if (!this.isValidPosition(toX, toZ)) return Infinity;

    const fromHeight = TerrainSystem.heightMap[fromZ][fromX];
    const toHeight = TerrainSystem.heightMap[toZ][toX];
    const heightDiff = toHeight - fromHeight;

    // Make rivers impassable
    if (toHeight === 0) {
        return Infinity;
    }

    // Base movement cost
    const isDiagonal = (fromX !== toX && fromZ !== toZ);
    let cost = isDiagonal ? 1.414 : 1.0;  // √2 for diagonal

    // Height change cost (climbing is expensive)
    if (heightDiff > 0) {
      cost += heightDiff * 2;  // Going uphill costs more
    } else if (heightDiff < 0) {
      cost += Math.abs(heightDiff) * 0.5;  // Going downhill costs less
    }

    // Roads are faster
    if (TerrainSystem.roadMap[toZ][toX] === 1) {
        cost *= 0.5;
    }

    return cost;
  },

  // Heuristic: Manhattan distance
  heuristic(gridX, gridZ, goalX, goalZ) {
    return Math.abs(gridX - goalX) + Math.abs(gridZ - goalZ);
  },

  // A* pathfinding algorithm
  findPath(startX, startZ, goalX, goalZ) {
    const startGrid = this.worldToGrid(startX, startZ);
    const goalGrid = this.worldToGrid(goalX, goalZ);

    // Validate positions
    if (!this.isValidPosition(startGrid.x, startGrid.z) ||
        !this.isValidPosition(goalGrid.x, goalGrid.z)) {
      debugLog('Pathfinding: Invalid start or goal position');
      return null;
    }

    // Node structure: { x, z, g, h, f, parent }
    const openList = [];
    const closedList = new Set();
    const startNode = {
      x: startGrid.x,
      z: startGrid.z,
      g: 0,
      h: this.heuristic(startGrid.x, startGrid.z, goalGrid.x, goalGrid.z),
      f: 0,
      parent: null
    };
    startNode.f = startNode.g + startNode.h;
    openList.push(startNode);

    // 8-directional movement (including diagonals)
    const directions = [
      { dx: 0, dz: -1 },  // North
      { dx: 1, dz: -1 },  // Northeast
      { dx: 1, dz: 0 },   // East
      { dx: 1, dz: 1 },   // Southeast
      { dx: 0, dz: 1 },   // South
      { dx: -1, dz: 1 },  // Southwest
      { dx: -1, dz: 0 },  // West
      { dx: -1, dz: -1 }  // Northwest
    ];

    let iterations = 0;
    const maxIterations = 2000;  // Prevent infinite loops

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

      // Check if we reached the goal
      if (current.x === goalGrid.x && current.z === goalGrid.z) {
        // Reconstruct path
        const path = [];
        let node = current;
        while (node !== null) {
          const world = this.gridToWorld(node.x, node.z);
          path.unshift({ x: world.x, z: world.z });
          node = node.parent;
        }
        debugLog('✅ Found path with ' + path.length + ' waypoints (' + iterations + ' iterations)');
        return path;
      }

      // Move current from open to closed
      openList.splice(currentIndex, 1);
      closedList.add(`${current.x},${current.z}`);

      // Check all neighbors
      for (const dir of directions) {
        const neighborX = current.x + dir.dx;
        const neighborZ = current.z + dir.dz;
        const neighborKey = `${neighborX},${neighborZ}`;

        // Skip if already evaluated or invalid
        if (closedList.has(neighborKey) || !this.isValidPosition(neighborX, neighborZ)) {
          continue;
        }

        // Calculate cost to neighbor
        const movementCost = this.getMovementCost(current.x, current.z, neighborX, neighborZ);
        const gScore = current.g + movementCost;

        // Check if neighbor is in open list
        let neighborNode = openList.find(n => n.x === neighborX && n.z === neighborZ);

        if (!neighborNode) {
          // New node
          neighborNode = {
            x: neighborX,
            z: neighborZ,
            g: gScore,
            h: this.heuristic(neighborX, neighborZ, goalGrid.x, goalGrid.z),
            f: 0,
            parent: current
          };
          neighborNode.f = neighborNode.g + neighborNode.h;
          openList.push(neighborNode);
        } else if (gScore < neighborNode.g) {
          // Better path found
          neighborNode.g = gScore;
          neighborNode.f = neighborNode.g + neighborNode.h;
          neighborNode.parent = current;
        }
      }
    }

    debugLog('⚠️ No path found or max iterations reached');
    return null;
  },

  // 3D pathfinding for air units (includes altitude)
  findPath3D(startX, startZ, startAlt, goalX, goalZ, goalAlt, unitType) {
    const startGrid = this.worldToGrid(startX, startZ);
    const goalGrid = this.worldToGrid(goalX, goalZ);

    const altRange = AltitudeSystem.getAltitudeRange(unitType);

    // Validate positions
    if (!this.isValidPosition(startGrid.x, startGrid.z) ||
        !this.isValidPosition(goalGrid.x, goalGrid.z)) {
      debugLog('3D Pathfinding: Invalid start or goal position');
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
        debugLog(`✅ Found 3D path with ${path.length} waypoints (${iterations} iterations)`);
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
          // New node
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
          // Better path found
          neighborNode.g = gScore;
          neighborNode.f = neighborNode.g + neighborNode.h;
          neighborNode.parent = current;
        }
      }
    }

    debugLog('⚠️ No 3D path found or max iterations reached');
    return null;
  },

  // 3D heuristic (Manhattan distance including altitude)
  heuristic3D(x, z, alt, goalX, goalZ, goalAlt) {
    return Math.abs(x - goalX) + Math.abs(z - goalZ) + Math.abs(alt - goalAlt) * 2;
  }
};

debugLog('✅ Pathfinding system initialized');

// Test air unit movement with altitude changes (after PathfindingSystem is ready)
UnitSystem.moveUnit(testFighter, 15, 15, 10);  // Move to high altitude
UnitSystem.moveUnit(testVTOL, -15, -15, 2);    // Move to low altitude

    // ═══════════════════════════════════════════════════════
    // STEP 6: Selection System
    // ═══════════════════════════════════════════════════════

    debugLog('Initializing selection system...');

    const SelectionSystem = {
      raycaster: new THREE.Raycaster(),
      mouse: new THREE.Vector2(),
      startPoint: new THREE.Vector2(),
      endPoint: new THREE.Vector2(),
      isDragging: false,
      selectionBox: null,
      selectedUnits: [],

      // Initialize raycaster
      init() {
        // Set raycaster threshold for better picking
        this.raycaster.params.Points = { threshold: 0.5 };
        this.raycaster.params.Line = { threshold: 0.5 };

        this.setupSelectionBox();
        this.attachEventListeners();
      },

      setupSelectionBox() {
        // Create selection box visual
        const geometry = new THREE.PlaneGeometry(1, 1);
        const material = new THREE.MeshBasicMaterial({
          color: 0x00ff00,
          transparent: true,
          opacity: 0.2,
          side: THREE.DoubleSide
        });
        this.selectionBox = new THREE.Mesh(geometry, material);
        this.selectionBox.rotation.x = -Math.PI / 2; // Lay flat on ground
        this.selectionBox.visible = false;
        scene.add(this.selectionBox);
      },

      attachEventListeners() {
        mountPoint.addEventListener('mousedown', this.onMouseDown.bind(this), false);
        mountPoint.addEventListener('mousemove', this.onMouseMove.bind(this), false);
        mountPoint.addEventListener('mouseup', this.onMouseUp.bind(this), false);
        mountPoint.addEventListener('contextmenu', this.onRightClick.bind(this), false);

        // Camera controls
        mountPoint.addEventListener('wheel', (e) => {
          e.preventDefault();
          const zoomSpeed = 0.1;
          const delta = e.deltaY > 0 ? 1 : -1;
          viewSize = Math.max(5, Math.min(50, viewSize + delta * zoomSpeed * viewSize));
          updateCamera();
        }, { passive: false });

        // Keyboard pan controls (WASD or Arrow keys)
        mountPoint.addEventListener('keydown', (e) => {
          const panSpeed = 2;
          switch(e.key.toLowerCase()) {
            case 'w':
            case 'arrowup':
              cameraTarget.z -= panSpeed;
              updateCamera();
              e.preventDefault();
              break;
            case 's':
            case 'arrowdown':
              cameraTarget.z += panSpeed;
              updateCamera();
              e.preventDefault();
              break;
            case 'a':
            case 'arrowleft':
              cameraTarget.x -= panSpeed;
              updateCamera();
              e.preventDefault();
              break;
            case 'd':
            case 'arrowright':
              cameraTarget.x += panSpeed;
              updateCamera();
              e.preventDefault();
              break;
          }
        });
      },

      onMouseDown(event) {
        event.preventDefault();
        debugLog('Mouse down at ' + event.clientX + ', ' + event.clientY);
        this.isDragging = true;
        this.startPoint.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.startPoint.y = -(event.clientY / window.innerHeight) * 2 + 1;
        this.endPoint.copy(this.startPoint); // Initialize endPoint
        this.selectionBox.visible = false; // Hide until drag is significant
      },

      onMouseMove(event) {
        event.preventDefault();
        if (!this.isDragging) return;

        this.endPoint.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.endPoint.y = -(event.clientY / window.innerHeight) * 2 + 1;

        // Update selection box visual
        const minX = Math.min(this.startPoint.x, this.endPoint.x);
        const maxX = Math.max(this.startPoint.x, this.endPoint.x);
        const minY = Math.min(this.startPoint.y, this.endPoint.y);
        const maxY = Math.max(this.startPoint.y, this.endPoint.y);

        const width = maxX - minX;
        const height = maxY - minY;

        if (width > 0.01 || height > 0.01) { // Only show if drag is significant
          this.selectionBox.visible = true;

          // Convert normalized device coordinates to world coordinates for the box
          this.raycaster.setFromCamera(this.startPoint, camera);
          const intersectsStart = this.raycaster.intersectObject(terrain);
          this.raycaster.setFromCamera(this.endPoint, camera);
          const intersectsEnd = this.raycaster.intersectObject(terrain);

          if (intersectsStart.length > 0 && intersectsEnd.length > 0) {
            const startWorld = intersectsStart[0].point;
            const endWorld = intersectsEnd[0].point;

            const boxWidth = Math.abs(endWorld.x - startWorld.x);
            const boxDepth = Math.abs(endWorld.z - startWorld.z);
            const boxCenterX = (startWorld.x + endWorld.x) / 2;
            const boxCenterZ = (startWorld.z + endWorld.z) / 2;

            this.selectionBox.scale.set(boxWidth, boxDepth, 1);
            this.selectionBox.position.set(boxCenterX, TerrainSystem.getHeightAt(boxCenterX, boxCenterZ) + 0.1, boxCenterZ);
          }
        } else {
          this.selectionBox.visible = false;
        }
      },

      onMouseUp(event) {
        event.preventDefault();
        debugLog('Mouse up at ' + event.clientX + ', ' + event.clientY);
        this.isDragging = false;
        this.selectionBox.visible = false;

        const rect = mountPoint.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        this.mouse.x = (mouseX / rect.width) * 2 - 1;
        this.mouse.y = -(mouseY / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, camera);

        // Check for unit selection - use hitboxes for easier clicking
        const selectableObjects = UnitSystem.units.map(unit => unit.hitbox);

        const intersects = this.raycaster.intersectObjects(selectableObjects, true);

        if (intersects.length > 0) {
          // Find unit by hitbox
          const clickedHitbox = intersects[0].object;
          const unitId = clickedHitbox.userData.unitId;
          const unit = UnitSystem.units.find(u => u.id === unitId);
          if (unit) {
            this.selectUnit(unit);
          }
        } else {
          // If no unit clicked, deselect all
          this.deselectAllUnits();
        }
      },

      selectUnit(unit) {
        this.deselectAllUnits(); // For single selection
        this.selectedUnits.push(unit);

        // Show visual feedback
        if (unit.selectionRing) {
          unit.selectionRing.visible = true;
        }

        debugLog('✅ UNIT SELECTED: ' + unit.id + ' (' + unit.type + ') at (' + unit.position.x.toFixed(1) + ', ' + unit.position.z.toFixed(1) + ')');
      },

      deselectAllUnits() {
        // Hide selection rings for all units
        this.selectedUnits.forEach(unit => {
          if (unit.selectionRing) {
            unit.selectionRing.visible = false;
          }
        });
        this.selectedUnits = [];
      },

      onRightClick(event) {
        event.preventDefault();

        // Only move if units are selected
        if (this.selectedUnits.length === 0) {
          return;
        }

        const rect = mountPoint.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        this.mouse.x = (mouseX / rect.width) * 2 - 1;
        this.mouse.y = -(mouseY / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, camera);

        // Raycast to terrain to get destination
        const intersects = this.raycaster.intersectObject(terrain);

        if (intersects.length > 0) {
          const destination = intersects[0].point;
          debugLog('✅ MOVE COMMAND: ' + this.selectedUnits.length + ' unit(s) to (' + destination.x.toFixed(1) + ', ' + destination.z.toFixed(1) + ')');

          // Command all selected units to move
          this.selectedUnits.forEach(unit => {
            UnitSystem.moveUnit(unit, destination.x, destination.z);
          });
        }
      },

      update(deltaTime) {
        // Update selection logic if needed (e.g., flashing selected units)
      }
    };

    SelectionSystem.init();
    debugLog('✅ Selection system initialized');

    // ═══════════════════════════════════════════════════════
    // STEP 7: Animation Loop
    // ═══════════════════════════════════════════════════════

    let animationFrameId;
    let lastTime = Date.now();

    function animate() {
      animationFrameId = requestAnimationFrame(animate);

      // Calculate delta time
      const now = Date.now();
      const deltaTime = (now - lastTime) / 1000;  // Convert to seconds
      lastTime = now;

      // Update Yuka AI system
      const yukaDelta = yukaTime.update().getDelta();
      yukaEntityManager.update(yukaDelta);

      // Sync Three.js mesh positions with Yuka vehicles
      UnitSystem.units.forEach(unit => {
        if (unit.yukaVehicle) {
          // Copy Yuka position to Three.js mesh (X and Z only, Y is handled separately)
          unit.position.x = unit.yukaVehicle.position.x;
          unit.position.z = unit.yukaVehicle.position.z;

          // --- Y-Position Smoothing ---
          const stats = UNIT_STATS[unit.type];
          let targetY;

          if (stats.type === 'air') {
            // Air units: Gradually change altitude level
            if (unit.targetAltitude !== undefined && unit.altitude !== unit.targetAltitude) {
              const altDiff = unit.targetAltitude - unit.altitude;
              const altStep = Math.sign(altDiff) * Math.min(Math.abs(altDiff), deltaTime * 2); // 2 levels/sec
              unit.altitude += altStep;
            }
            
            // Target Y is based on altitude relative to sea-level, but with terrain avoidance
            const seaLevelAltitude = AltitudeSystem.getYPosition(0, unit.altitude);
            const terrainHeight = TerrainSystem.getHeightAt(unit.position.x, unit.position.z);
            const minSafeAltitude = terrainHeight + 2.0; // Must be at least 2 units above ground

            targetY = Math.max(seaLevelAltitude, minSafeAltitude);
          } else {
            // Ground units: Target Y is on the terrain surface
            const terrainHeight = TerrainSystem.getHeightAt(unit.position.x, unit.position.z);
            // Adjusted offset to balance between hovering and clipping
            const heightOffset = unit.type === 'ARTILLERY' ? 1.2 : 0.6;
            targetY = terrainHeight + heightOffset;
          }

          // Smoothly interpolate the unit's Y position towards the target Y
          // Use a higher interpolation factor for ground units to make them stick to terrain more closely
          const interpolationFactor = stats.type === 'ground' ? 10 : 5;
          unit.position.y = THREE.MathUtils.lerp(unit.position.y, targetY, deltaTime * interpolationFactor);

          // Update Yuka vehicle Y to match the smoothed position
          unit.yukaVehicle.position.y = unit.position.y;

          // --- Sanity Checks and Final Updates ---
          if (isNaN(unit.position.x) || isNaN(unit.position.y) || isNaN(unit.position.z)) {
            console.error(`Unit ${unit.id} has invalid position:`, unit.position);
          } else {
            // Update mesh position
            unit.mesh.position.set(unit.position.x, unit.position.y, unit.position.z);
          }

          // --- Rotation and Tilting ---
          const yukaVelocity = unit.yukaVehicle.velocity;
          const isMoving = yukaVelocity.length() > 0.1;

          if (isMoving) {
            unit.rotation = Math.atan2(yukaVelocity.x, yukaVelocity.z);
          }

          const headingQuaternion = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), unit.rotation);
          let finalQuaternion = headingQuaternion;

          // Ground units tilt with the terrain
          if (stats.type === 'ground') {
            const terrainNormal = TerrainSystem.getNormalAt(unit.position.x, unit.position.z);
            const upVector = new THREE.Vector3(0, 1, 0);
            const tiltQuaternion = new THREE.Quaternion().setFromUnitVectors(upVector, terrainNormal);
            finalQuaternion = tiltQuaternion.multiply(headingQuaternion);
          }

          if (isNaN(finalQuaternion.x) || isNaN(finalQuaternion.y) || isNaN(finalQuaternion.z) || isNaN(finalQuaternion.w)) {
            console.error(`Unit ${unit.id} has invalid finalQuaternion.`);
          } else {
            // Smoothly interpolate to the final rotation
            unit.mesh.quaternion.slerp(finalQuaternion, deltaTime * 7);
          }

          // Update hitbox position
          if (unit.hitbox) {
            unit.hitbox.position.set(unit.position.x, unit.position.y, unit.position.z);
            unit.hitbox.rotation.y = unit.rotation;
          }

          // Update selection ring position (on ground)
          if (unit.selectionRing) {
            const terrainHeight = TerrainSystem.getHeightAt(unit.position.x, unit.position.z);
            unit.selectionRing.position.set(unit.position.x, terrainHeight + 0.2, unit.position.z);
          }

          // Update altitude indicator for air units
          if (unit.altitudeIndicator) {
            const terrainHeight = TerrainSystem.getHeightAt(unit.position.x, unit.position.z);
            unit.altitudeIndicator.position.set(unit.position.x, terrainHeight + 0.1, unit.position.z);
          }
        }
      });

      // Update units (now just checks arrival and handles combat)
      UnitSystem.update(deltaTime);
      CombatSystem.updateProjectiles(deltaTime);
      // Update selection system
      SelectionSystem.update(deltaTime);

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

    debugLog('Starting animation loop...');
    animate();

    console.log('═══════════════════════════════════════════════════');
    console.log(`✅ Warzone Lite ${APPLET_VERSION}: READY!`);
    console.log('═══════════════════════════════════════════════════');
    debugLog('✅ READY! Left-click to select, Right-click to move');

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
