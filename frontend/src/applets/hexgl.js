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
// Full path: axon_bbs/frontend/src/applets/hexgl.js
//
// Original HexGL Game Logic and Assets:
// MIT License - Copyright (c) Thibaut Despoulain (BKcore)
//
// This version has been updated to use a modern version of THREE.js (r128)
// and relies on the AppletRunner to load its dependencies.

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
        if(command === 'getAppletInfo') {
           resolve({ name: 'HexGL', parameters: { asset_hash: 'SIMULATED_ASSET_HASH' } });
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
  // Advanced & Viewer Applet API
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); },
  getAttachmentBlob: function(hash) { return this._postMessage('getAttachmentBlob', { hash }); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    const appletContainer = document.getElementById('applet-root');
    
    // --- Debug Console Setup ---
    const debugLog = (message) => {
        if (window.BBS_DEBUG_MODE !== true) return;
        const debugDialog = document.getElementById('debug-dialog');
        if (!debugDialog) return;
        const logEntry = document.createElement('div');
        logEntry.textContent = `> ${message}`;
        debugDialog.appendChild(logEntry);
        debugDialog.scrollTop = debugDialog.scrollHeight;
    };
    
    try {
        console.log("HexGL Applet (Modernized Loader): Execution begins.");
        
        // --- Helper function to dynamically load game assets from the BBS network ---
        async function loadAssetPackage(hash, progressCallback) {
            debugLog("Entering loadAssetPackage function...");
            progressCallback({ status: 'Downloading asset package...', percent: 15 });
            
            if (typeof JSZip === 'undefined') {
                throw new Error("JSZip library is not loaded. Cannot unpack assets.");
            }

            const assetBlob = await window.bbs.getAttachmentBlob(hash);
            if (!assetBlob) throw new Error("Failed to retrieve asset package from BBS. Check if the asset_hash is correct.");

            progressCallback({ status: 'Unzipping assets in memory...', percent: 40 });
            const zip = await JSZip.loadAsync(assetBlob);
            const assets = {};
            const promises = [];
            const filesInZip = Object.keys(zip.files).filter(name => !zip.files[name].dir);
            const totalFiles = filesInZip.length;
            let filesProcessed = 0;

            filesInZip.forEach((relativePath) => {
                const zipEntry = zip.files[relativePath];
                const promise = (zipEntry.name.endsWith('.js') ? zipEntry.async('string') : zipEntry.async('blob')).then(content => {
                    const objectURL = zipEntry.name.endsWith('.js') ? content : URL.createObjectURL(content);
                    const fileName = relativePath.split('/').pop();
                    assets[fileName] = objectURL;
                    filesProcessed++;
                    const progress = 40 + Math.round((filesProcessed / totalFiles) * 60);
                    progressCallback({ status: `Unpacking: ${fileName}`, percent: progress });
                });
                promises.push(promise);
            });

            await Promise.all(promises);
            debugLog("Asset package successfully unzipped into memory.");
            progressCallback({ status: 'Assets ready.', percent: 100 });
            return assets;
        }
        
        // --- Render initial HTML structure ---
        const htmlContent = `
            <style>
              body, html { margin:0; padding:0; overflow:hidden; font-family:BebasNeueRegular, sans-serif; background-color:#151515; }
              #global { position:absolute; top:0; left:0; width:100%; height:100%; z-index:10; background-repeat:repeat; }
              #title { position:absolute; top:50%; left:50%; width:490px; height:120px; margin:-190px 0 0 -245px; z-index:20; background-repeat:no-repeat; }
              #menucontainer { position:absolute; top:50%; left:50%; width:300px; height:200px; margin:-30px 0 0 -150px; z-index:20; }
              #menu { position:relative; width:100%; height:100%; color:#eee; text-align:center; font-size:3.5em; cursor:pointer; text-shadow:0px 0px 10px #000; }
              #menu div { position:absolute; width:100%; }
              #menu div:hover { color:#fff; text-shadow:0px 0px 10px #fff; }
              #start { top:0px; } #s-controlType { top:70px; } #s-quality { top:120px; } #s-hud { top:170px; } #s-godmode { top:220px; } #s-credits { top:270px; }
              #credits { position:absolute; top:50%; left:50%; width:500px; height:400px; margin:-200px 0 0 -250px; color:#eee; z-index:20; text-align:center; display:none; }
              #credits h1 { font-size:3em; } #credits h2 { font-size:2em; color:#ccc; } #credits p { font-size:1.5em; } #credits a { color:#fff; } #credits a:hover { color:#ff0; }
              #step-2, #step-5 { position:absolute; top:0; left:0; width:100%; height:100%; z-index:10; }
              #step-2 #ctrl-help, #step-5 #ctrl-help { position:absolute; width:100%; top:50%; margin-top:-0.7em; color:#eee; text-align:center; font-size:2em; }
              #step-3 { position:absolute; top:50%; left:50%; width:400px; height:100px; margin:-50px 0 0 -200px; z-index:10; color:#eee; text-align:center; }
              #step-3 #loading-status { font-size:2em; }
              #step-3 #progressbar { width:400px; height:20px; border:2px solid #fff; margin-top:10px; }
              #step-3 #progressbar div { width:0%; height:100%; background-color:#fff; }
              #step-3 #loading-file { font-size: 1em; color: #aaa; margin-top: 5px; }
              #step-4 { position:absolute; top:0; left:0; width:100%; height:100%; z-index:5; }
              #step-4 #overlay { position:absolute; top:0; left:0; width:100%; height:100%; z-index:15; }
              #step-4 #main { position:absolute; top:0; left:0; width:100%; height:100%; z-index:10; }
              #step-5 #time { position:absolute; width:100%; top:50%; margin-top:-1.4em; color:#eee; text-align:center; font-size:4em; }
              #debug-dialog { display: none; position: absolute; bottom: 10px; right: 10px; width: 350px; height: 250px; background-color: rgba(0,0,0,0.8); border: 1px solid #4a5568; border-radius: 5px; color: #9AE6B4; font-family: monospace; font-size: 12px; overflow-y: scroll; padding-top: 25px; z-index: 1000; }
              #debug-header { position: absolute; top: 0; left: 0; right: 0; background-color: #4a5568; color: white; font-weight: bold; padding: 3px; cursor: move; user-select: none; }
            </style>
            <div id="debug-dialog"><div id="debug-header">DEBUG CONSOLE</div></div>
            <div id="step-1" style="display: block;">
              <div id="global"></div><div id="title"></div>
              <div id="menucontainer"><div id="menu">
                  <div id="start">Start</div><div id="s-controlType">Controls: Keyboard</div>
                  <div id="s-quality">Quality: HIGH</div><div id="s-hud">HUD: ON</div>
                  <div id="s-godmode" style="display: none;">Godmode: OFF</div><div id="s-credits">Credits</div>
              </div></div>
            </div>
            <div id="step-2" style="display: none;"><div id="ctrl-help">Click/Touch/Space to continue.</div></div>
            <div id="step-3" style="display: none;">
              <div id="loading-status"></div>
              <div id="progressbar"><div style="width: 0%;"></div></div>
              <div id="loading-file" style="font-size: 1em; color: #aaa; margin-top: 5px;"></div>
            </div>
            <div id="step-4" style="display: none;"><div id="overlay"></div><div id="main"></div></div>
            <div id="step-5" style="display: none;"><div id="time"></div><div id="ctrl-help">Click/Touch to continue.</div></div>
            <div id="credits" style="display: none;"><h1>HexGL</h1><p>by <a href="http://bkcore.com">Thibaut Despoulain</a></p><h2>Music</h2><p>"Cipher" by <a href="http://www.kevinmacleod.com">Kevin MacLeod</a></p><h2>Special Thanks</h2><p><a href="http://mrdoob.com/">Mr.doob</a> and the <a href="https://github.com/mrdoob/three.js/">three.js</a> team</p><a href="#" id="credits-back">Back</a></div>
        `;
        appletContainer.innerHTML = htmlContent;
        
        // --- Make debug console draggable ---
        if (window.BBS_DEBUG_MODE === true) {
            document.getElementById('debug-dialog').style.display = 'block';
            const debugDialog = document.getElementById('debug-dialog');
            const debugHeader = document.getElementById('debug-header');
            let isDragging = false, offsetX, offsetY;
            debugHeader.onmousedown = (e) => { isDragging = true; offsetX = e.clientX - debugDialog.offsetLeft; offsetY = e.clientY - debugDialog.offsetTop; };
            document.onmousemove = (e) => { if (isDragging) { debugDialog.style.left = `${e.clientX - offsetX}px`; debugDialog.style.top = `${e.clientY - offsetY}px`; } };
            document.onmouseup = () => { isDragging = false; };
        }
        
        debugLog("HexGL Applet: Initializing...");

        // --- Game engine logic (Fully patched and re-ordered for THREE.js r128) ---
        var bkcore = { hexgl: {} };
        bkcore.hexgl.tracks = {
            cityscape: {
                getHeight: function(x, z) { return 0; },
                getPoint: function(position) { return position; },
                getNormal: function(position) { return new THREE.Vector3(0, 1, 0); }
            }
        };
        bkcore.hexgl.ships = { feisar: {} };

        // Custom JSON model parser for old THREE.js JSON format (v3.1)
        bkcore.hexgl.ModelLoader = function() {
            this.assets = null;  // Will be set when assets are loaded

            this.parse = function(jsonData) {
                debugLog("ModelLoader.parse: Starting parse. Format version: " + (jsonData.metadata ? jsonData.metadata.formatVersion : "unknown"));
                const geometry = new THREE.BufferGeometry();
                const materials = [];
                const textureLoader = new THREE.TextureLoader();

                // Parse materials first
                if (jsonData.materials) {
                    debugLog("ModelLoader.parse: Processing " + jsonData.materials.length + " materials");
                    for (let i = 0; i < jsonData.materials.length; i++) {
                        const mat = jsonData.materials[i];
                        const color = mat.DbgColor !== undefined ? mat.DbgColor : 0xffffff;

                        const materialProps = {
                            color: color,
                            emissive: 0x000000,
                            specular: 0x333333,
                            shininess: mat.specularCoef || 30,
                            side: THREE.DoubleSide,
                            wireframe: false,
                            flatShading: false
                        };

                        // Load texture maps if available
                        if (this.assets && mat.mapDiffuse) {
                            const textureName = mat.mapDiffuse.split('/').pop();
                            if (this.assets[textureName]) {
                                debugLog("  Material[" + i + "]: Loading diffuse texture: " + textureName);
                                materialProps.map = textureLoader.load(this.assets[textureName]);
                            }
                        }

                        debugLog("  Material[" + i + "]: DbgColor=" + (mat.DbgColor !== undefined ? "0x" + mat.DbgColor.toString(16) : "undefined") + ", using 0x" + color.toString(16) + (materialProps.map ? " with texture" : ""));
                        const material = new THREE.MeshPhongMaterial(materialProps);
                        materials.push(material);
                    }
                } else {
                    debugLog("ModelLoader.parse: No materials found, using default green");
                    materials.push(new THREE.MeshPhongMaterial({ color: 0x00ff00, emissive: 0x111111, side: THREE.DoubleSide }));
                }

                // Parse vertices (flat array of x,y,z values)
                const vertices = jsonData.vertices || [];
                const normals = jsonData.normals || [];
                const uvs = jsonData.uvs && jsonData.uvs[0] ? jsonData.uvs[0] : [];

                // Parse faces - OLD THREE.js format uses bit flags
                // Face format: [type, vertex_indices..., material_index, uv_indices..., normal_indices...]
                const faces = jsonData.faces || [];
                const indices = [];
                const finalVertices = [];
                const finalNormals = [];
                const finalUVs = [];

                let offset = 0;
                let vertexIndex = 0;

                while (offset < faces.length) {
                    const type = faces[offset++];
                    const isQuad = (type & 1) === 1;
                    const hasMaterial = (type & 2) === 2;
                    const hasFaceUv = (type & 4) === 4;
                    const hasFaceVertexUv = (type & 8) === 8;
                    const hasFaceNormal = (type & 16) === 16;
                    const hasFaceVertexNormal = (type & 32) === 32;
                    const hasFaceColor = (type & 64) === 64;
                    const hasFaceVertexColor = (type & 128) === 128;

                    const nVertices = isQuad ? 4 : 3;
                    const vertexIndices = [];

                    for (let i = 0; i < nVertices; i++) {
                        const idx = faces[offset++];
                        vertexIndices.push(idx);

                        // Copy vertex position
                        finalVertices.push(vertices[idx * 3], vertices[idx * 3 + 1], vertices[idx * 3 + 2]);
                    }

                    if (hasMaterial) offset++; // Skip material index
                    if (hasFaceUv) offset++; // Skip face UV

                    if (hasFaceVertexUv) {
                        for (let i = 0; i < nVertices; i++) {
                            const uvIdx = faces[offset++];
                            if (uvs.length > 0) {
                                finalUVs.push(uvs[uvIdx * 2], uvs[uvIdx * 2 + 1]);
                            } else {
                                finalUVs.push(0, 0);
                            }
                        }
                    } else {
                        for (let i = 0; i < nVertices; i++) {
                            finalUVs.push(0, 0);
                        }
                    }

                    if (hasFaceNormal) offset++; // Skip face normal

                    if (hasFaceVertexNormal) {
                        for (let i = 0; i < nVertices; i++) {
                            const nIdx = faces[offset++];
                            if (normals.length > 0) {
                                finalNormals.push(normals[nIdx * 3], normals[nIdx * 3 + 1], normals[nIdx * 3 + 2]);
                            } else {
                                finalNormals.push(0, 1, 0);
                            }
                        }
                    } else {
                        for (let i = 0; i < nVertices; i++) {
                            finalNormals.push(0, 1, 0);
                        }
                    }

                    if (hasFaceColor) offset++; // Skip face color
                    if (hasFaceVertexColor) {
                        for (let i = 0; i < nVertices; i++) {
                            offset++; // Skip vertex colors
                        }
                    }

                    // Create triangles
                    if (isQuad) {
                        indices.push(vertexIndex, vertexIndex + 1, vertexIndex + 2);
                        indices.push(vertexIndex, vertexIndex + 2, vertexIndex + 3);
                        vertexIndex += 4;
                    } else {
                        indices.push(vertexIndex, vertexIndex + 1, vertexIndex + 2);
                        vertexIndex += 3;
                    }
                }

                geometry.setAttribute('position', new THREE.Float32BufferAttribute(finalVertices, 3));
                geometry.setAttribute('normal', new THREE.Float32BufferAttribute(finalNormals, 3));
                geometry.setAttribute('uv', new THREE.Float32BufferAttribute(finalUVs, 2));
                geometry.setIndex(indices);

                debugLog("ModelLoader.parse: Created geometry with " + (finalVertices.length / 3) + " vertices and " + (indices.length / 3) + " triangles");
                debugLog("ModelLoader.parse: Returning " + materials.length + " material(s)");

                return { geometry, materials: materials.length > 0 ? materials[0] : materials };
            };
        };

        bkcore.hexgl.Audio = function (a) { this.assets = a; this.sources = { engine: null }; this.init = function () { } };
        bkcore.hexgl.Camera = function (a) { var b = this; this.game = a; this.camera = null; this.target = new THREE.Vector3(0, 0, 0); this.height = 2; this.offsetHeight = 0; this.distance = 10; this.flying = false; this.load = function (a) { b.camera = new THREE.PerspectiveCamera(70, b.game.width / b.game.height, 0.1, 5000); b.target = a.position; b.camera.position.set(b.target.x, b.target.y + b.height, b.target.z + b.distance); b.camera.lookAt(b.target); debugLog("Camera.load: Camera positioned at (" + b.camera.position.x + "," + b.camera.position.y + "," + b.camera.position.z + ") looking at (" + b.target.x + "," + b.target.y + "," + b.target.z + ")"); }; this.resize=function(a,c){b.camera.aspect=a/c;b.camera.updateProjectionMatrix()};this.update=function(){ if(b.camera) { b.camera.position.set(b.target.x, b.target.y + b.height + b.offsetHeight, b.target.z + b.distance); b.camera.lookAt(b.target); } }};
        bkcore.hexgl.Controls = function (a) { this.game = a; this.init = function () { } };
        bkcore.hexgl.FX = function (a) { this.game = a; this.load = function (b) { b() } };
        bkcore.hexgl.HUD = function (a) { this.game = a; this.init = function () { }; this.update=function(){}};
        bkcore.hexgl.Lap = function (a) { this.game = a; this.time = function (a) {var b=new Date(a);var c=String(b.getMinutes());var d=String(b.getSeconds());a=String(b.getMilliseconds());return c.length<2&&(c="0"+c),d.length<2&&(d="0"+d),a.length<2&&(a="0"+a),a.length<3&&(a="0"+a),c+":"+d+":"+a} };
        bkcore.hexgl.Race = function(a){this.game=a;this.track=null;this.load=function(b,c){var d=this;this.track=b;debugLog("Race.load: Parsing track data...");var e=this.game.loader.parse(JSON.parse(this.game.assets["track.js"]));debugLog("Race.load: Creating track mesh...");d.track.mesh=new THREE.Mesh(e.geometry,e.materials);e.geometry.computeBoundingBox();var bbox=e.geometry.boundingBox;debugLog("Race.load: Track bounding box: min(" + bbox.min.x.toFixed(1) + "," + bbox.min.y.toFixed(1) + "," + bbox.min.z.toFixed(1) + ") max(" + bbox.max.x.toFixed(1) + "," + bbox.max.y.toFixed(1) + "," + bbox.max.z.toFixed(1) + ")");d.track.mesh.scale.set(0.05,0.05,0.05);d.track.mesh.position.set(0,-10,0);this.game.scene.add(d.track.mesh);debugLog("Race.load: Track mesh added to scene at pos(0,-10,0) scale(0.05,0.05,0.05). Vertices: " + (e.geometry.attributes.position ? e.geometry.attributes.position.count : 0));c()}};
        bkcore.hexgl.ShipControls = function(a){this.game=a;this.ship=null;this.load=function(b,c){var d=this;this.ship={position:new THREE.Vector3(0,1.5,0)};debugLog("ShipControls.load: Parsing ship data...");var e=this.game.loader.parse(JSON.parse(this.game.assets["feisar.js"]));debugLog("ShipControls.load: Creating ship mesh...");this.ship.mesh=new THREE.Mesh(e.geometry,e.materials);this.ship.mesh.scale.set(1,1,1);this.ship.mesh.position.copy(this.ship.position);this.ship.mesh.rotation.y=Math.PI;e.geometry.computeBoundingBox();var bbox=e.geometry.boundingBox;debugLog("ShipControls.load: Ship bounding box: min(" + bbox.min.x.toFixed(1) + "," + bbox.min.y.toFixed(1) + "," + bbox.min.z.toFixed(1) + ") max(" + bbox.max.x.toFixed(1) + "," + bbox.max.y.toFixed(1) + "," + bbox.max.z.toFixed(1) + ")");var refBox=new THREE.Mesh(new THREE.BoxGeometry(1,1,1),new THREE.MeshBasicMaterial({color:0xff00ff,wireframe:true}));refBox.position.set(0,1.5,-3);this.game.scene.add(refBox);debugLog("ShipControls.load: Added reference box at (0,1.5,-3)");this.game.scene.add(this.ship.mesh);debugLog("ShipControls.load: Ship mesh added to scene at pos(" + this.ship.mesh.position.x + "," + this.ship.mesh.position.y + "," + this.ship.mesh.position.z + ") scale(" + this.ship.mesh.scale.x + "," + this.ship.mesh.scale.y + "," + this.ship.mesh.scale.z + "). Vertices: " + (e.geometry.attributes.position ? e.geometry.attributes.position.count : 0));c()};this.update=function(){}};
        bkcore.hexgl.HexGL = function (a) { var b = this; this.document = a.document; this.width = a.width; this.height = a.height; this.container = a.container; this.overlay = a.overlay; this.gameover = a.gameover; this.quality = a.quality; this.hud = a.hud; this.controlType = a.controlType; this.godmode = a.godmode; this.time = a.time; this.assets = a.assets; this.loader = new bkcore.hexgl.ModelLoader(); this.loader.assets = a.assets; this.active = false; this.playing = false; this.score = 0; this.timer = { start: 0, end: 0 }; this.difficulty = 2; this.speed = 200; this.Lap = new bkcore.hexgl.Lap(this); this.Controls = new bkcore.hexgl.Controls(this); this.ShipControls = new bkcore.hexgl.ShipControls(this); this.Camera = new bkcore.hexgl.Camera(this); this.HUD = new bkcore.hexgl.HUD(this); this.Race = new bkcore.hexgl.Race(this); this.FX = new bkcore.hexgl.FX(this); this.Audio = new bkcore.hexgl.Audio(this.assets); this.init = function () { debugLog("HexGL.init: Starting initialization..."); b.active = true; b.scene = new THREE.Scene; b.scene.fog = new THREE.Fog(0x151515, 100, 1500); var ambientLight = new THREE.AmbientLight(0xffffff, 1.0); b.scene.add(ambientLight); var directionalLight1 = new THREE.DirectionalLight(0xffffff, 0.8); directionalLight1.position.set(10, 20, 10); b.scene.add(directionalLight1); var directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.5); directionalLight2.position.set(-10, -10, -10); b.scene.add(directionalLight2); debugLog("HexGL.init: Lights added to scene (ambient + 2 directional)"); b.renderer=new THREE.WebGLRenderer({antialias:!0});b.renderer.setSize(b.width,b.height);b.renderer.setClearColor(0x151515);b.container.appendChild(b.renderer.domElement);debugLog("HexGL.init: Renderer created and added to DOM. Canvas size: " + b.width + "x" + b.height);b.Race.load(bkcore.hexgl.tracks.cityscape, function () { debugLog("HexGL.init: Race loaded, loading FX..."); b.FX.load(function () { debugLog("HexGL.init: FX loaded, loading ship..."); b.ShipControls.load(bkcore.hexgl.ships.feisar, function () { debugLog("HexGL.init: Ship loaded, setting up camera..."); b.Camera.load(b.ShipControls.ship); b.Controls.init(); b.HUD.init(); b.Audio.init(); b.playing = true; b.timer.start = Date.now(); debugLog("HexGL.init: Starting animation loop. Camera pos: (" + b.Camera.camera.position.x + "," + b.Camera.camera.position.y + "," + b.Camera.camera.position.z + ")"); b.animate() }) }) }) }; this.start = function () { b.init() }; this.animate = function () { requestAnimationFrame(b.animate); b.loop() }; this.loop = function () { if (b.active) { b.Camera.update(); b.renderer.render(b.scene, b.Camera.camera) } }; this.resize = function (a, c) { b.width = a; b.height = c; b.Camera.resize(a, c); b.renderer.setSize(b.width, b.height) }; this.gameOver = function () { b.playing = false; b.timer.end = Date.now(); b.gameover.style.display = "block"; b.time.innerHTML = b.Lap.time(b.timer.end - b.timer.start); var a = function () { b.gameover.style.display = "none"; b.container.style.cursor = "pointer"; b.document.getElementById("step-1").style.display = "block"; b.active = false; b.container.innerHTML = "" }; b.gameover.addEventListener("click", a, !1) }; (function () { var a = new THREE.Vector3; return function () { var b = this.getForward(this.mesh, a); return this.ray.set(this.mesh.position, b), this.ray.intersectObjects(this.scene.children) } }).call(this) };

        // --- Applet Entry Point ---
        if (!(window.WebGLRenderingContext && document.createElement('canvas').getContext('webgl'))) {
            document.getElementById('start').innerHTML = 'WebGL Not Supported!';
        } else {
             const startButton = document.getElementById('start');
             startButton.onclick = async () => {
                try {
                    startButton.textContent = 'Loading...';
                    startButton.style.pointerEvents = 'none';
                    debugLog("Start button clicked.");

                    document.getElementById('step-1').style.display = 'none';
                    document.getElementById('step-3').style.display = 'block';
                    const progressbar = document.getElementById('progressbar').firstElementChild;
                    const loadingStatus = document.getElementById('loading-status');
                    const loadingFile = document.getElementById('loading-file');
                    
                    const progressCallback = (p) => {
                        loadingStatus.textContent = p.status;
                        progressbar.style.width = `${p.percent}%`;
                        if (p.status.startsWith('Unpacking:')) {
                            loadingFile.textContent = p.status.substring(11);
                        } else {
                            loadingFile.textContent = '';
                        }
                    };

                    progressCallback({ status: 'Fetching configuration...', percent: 1 });
                    const appletInfo = await window.bbs.getAppletInfo();
                    const params = appletInfo?.parameters;
                    debugLog("Applet info received.");

                    if (!params || !params.asset_hash) {
                        throw new Error("SysOp Configuration Error: The applet's parameters must include 'asset_hash'.");
                    }
                    
                    const assets = await loadAssetPackage(params.asset_hash, progressCallback);

                    debugLog("Checkpoint: Applying dynamic CSS...");
                    const cssContent = `
                        @font-face {
                            font-family: 'BebasNeueRegular';
                            src: url('${assets['BebasNeue-webfont.eot']}');
                            src: url('${assets['BebasNeue-webfont.eot']}?#iefix') format('embedded-opentype'),
                                 url('${assets['BebasNeue-webfont.woff']}') format('woff'),
                                 url('${assets['BebasNeue-webfont.ttf']}') format('truetype'),
                                 url('${assets['BebasNeue-webfont.svg']}#BebasNeueRegular') format('svg');
                        }
                        #global { background-image: url(${assets['title.png']}); }
                        #title { background-image: url(${assets['hexgl.png']}); }
                    `;
                    const styleTag = document.createElement('style');
                    styleTag.appendChild(document.createTextNode(cssContent));
                    document.head.appendChild(styleTag);
                    debugLog("Checkpoint: CSS applied.");
                    
                    setTimeout(() => {
                        try {
                            debugLog("Checkpoint: Hiding loading screen, showing game container...");
                            document.getElementById('step-3').style.display = 'none';
                            document.getElementById('step-4').style.display = 'block';
                            
                            debugLog("Checkpoint: Instantiating HexGL object...");
                            var hexGL = new bkcore.hexgl.HexGL({
                                document: document,
                                width: window.innerWidth,
                                height: window.innerHeight,
                                container: document.getElementById('main'),
                                overlay: document.getElementById('overlay'),
                                gameover: document.getElementById('step-5'),
                                quality: 2, // High
                                hud: true,
                                controlType: 0, // Keyboard
                                godmode: false,
                                time: document.getElementById('time'),
                                assets: assets
                            });
                            
                            debugLog("Checkpoint: Adding resize listener...");
                            window.addEventListener('resize', function() { hexGL.resize(window.innerWidth, window.innerHeight); });
                            
                            debugLog("Checkpoint: Starting game engine...");
                            hexGL.start();
                            debugLog("Checkpoint: Game engine started.");
                        } catch (e) {
                            console.error("Error during game initialization:", e);
                            debugLog(`INITIALIZATION ERROR: ${e.message}`);
                            appletContainer.innerHTML = `<div style="padding: 20px; color: #ffdddd; background-color: #330000; border: 1px solid #880000; font-family: monospace;"><h2>Applet Error</h2><p>An error occurred during game engine startup:</p><p>${e.message}</p></div>`;
                        }
                    }, 500);

                } catch (e) {
                    console.error("Failed during asset loading or game startup:", e);
                    debugLog(`ERROR: ${e.message}`);
                    appletContainer.innerHTML = `<div style="padding: 20px; color: #ffdddd; background-color: #330000; border: 1px solid #880000; font-family: monospace;"><h2>Applet Error</h2><p>${e.message}</p></div>`;
                }
             };
        }

    } catch (e) {
        console.error("HexGL Applet: A fatal error occurred during initialization.", e);
        if(appletContainer) {
            appletContainer.innerHTML = `<div style="padding: 20px; color: #ffdddd; background-color: #330000; border: 1px solid #880000; font-family: monospace;"><h2>Applet Error</h2><p>${e.message}</p><pre>${e.stack}</pre></div>`;
        }
    }
})();
