// AiRobotWars v1.0 - AI vs AI Robot Battle Simulation
// Copyright (C) 2025 - Licensed under GPL v3
//
// A C-Robots style game where AI models compete by writing robot control scripts
// Features birds-eye 3D view using Three.js

// --- Start of Applet API Helper (MANDATORY) ---
window.bbs = {
    _callbacks: {},
    _requestId: 0,
    _handleMessage: function (event) {
        const { command, payload, requestId, error } = event.data;
        if (command && command.startsWith('response_') && this._callbacks[requestId]) {
            const { resolve, reject } = this._callbacks[requestId];
            if (error) { reject(new Error(error)); } else { resolve(payload); }
            delete this._callbacks[requestId];
        }
    },
    _postMessage: function (command, payload = {}) {
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
                    resolve({ id: 'test', name: 'AiRobotWars', parameters: {} });
                } else {
                    resolve({});
                }
            }
        });
    },
    getUserInfo: function () { return this._postMessage('getUserInfo'); },
    getData: function () { return this._postMessage('getData'); },
    saveData: function (newData) { return this._postMessage('saveData', newData); },
    getAppletInfo: function () { return this._postMessage('getAppletInfo'); },
    postEvent: function (eventData) { return this._postMessage('postEvent', eventData); },
    readEvents: function () { return this._postMessage('readEvents'); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---

// --- Main Applet Execution ---
(async function () {
    try {
        const APPLET_VERSION = 'v2.5.8 - Recording Fix';

        // ═══════════════════════════════════════════════════════
        // Debug Console
        // ═══════════════════════════════════════════════════════

        function debugLog(msg) {
            if (!window.BBS_DEBUG_MODE) return;
            const ts = new Date().toISOString().split('T')[1].slice(0, -1);
            const log = '[RW ' + ts + '] ' + msg;
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

        if (window.BBS_DEBUG_MODE) {
            const dp = document.createElement('div');
            dp.id = 'debug-panel';
            dp.style.cssText = 'position:fixed;bottom:0;right:0;width:400px;max-height:200px;background:rgba(0,0,0,0.9);border:1px solid #32cd32;overflow-y:auto;padding:10px;z-index:9999;font-size:0.7rem;color:#32cd32;font-family:monospace;';
            document.body.appendChild(dp);
            const versionDiv = document.createElement('div');
            versionDiv.textContent = '=== AI ROBOT WARS ' + APPLET_VERSION + ' ===';
            versionDiv.style.cssText = 'font-size:0.8rem;color:#ffff00;font-weight:bold;margin-bottom:5px;border-bottom:1px solid #32cd32;padding-bottom:3px;';
            dp.appendChild(versionDiv);
        }

        console.log('═══════════════════════════════════════════════════');
        console.log(`🤖 AI Robot Wars ${APPLET_VERSION}`);
        console.log('═══════════════════════════════════════════════════');
        debugLog('Starting applet...');

        // ═══════════════════════════════════════════════════════
        // Load External Libraries
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

        // ═══════════════════════════════════════════════════════
        // Game Constants
        // ═══════════════════════════════════════════════════════

        const ARENA_SIZE = 1000;
        const ROBOT_SIZE = 15; // Collision radius
        const GAME_SPEED = 60; // FPS (approx)

        // Game Balance Constants (v2.0)
        const MAX_ENERGY = 2500; // Reduced from 5000 (Vampire Mode)
        const ENERGY_DRAIN_IDLE = 0.5; // High "Vampire" drain (was 0.01)
        const ENERGY_DRAIN_MOVE = 0.05; // Per unit of speed
        const ENERGY_DRAIN_FIRE = 5; // Firing costs energy
        const ENERGY_DRAIN_MINE = 15; // Mines are expensive
        const ENERGY_DRAIN_SCAN = 0.2; // Scanning costs energy

        // Base Stations (v2.0)
        const BASE_RADIUS = 80;
        const BASE_RECHARGE_RATE = 60; // Energy per tick (Buffed v2.2.1)
        const BASE_REPAIR_RATE = 1.0; // Health per tick (Buffed v2.2.1)
        const BASES = [
            { x: 100, y: 100, color: 0x60a5fa }, // Blue Base (Top-Left)
            { x: 900, y: 900, color: 0xf87171 }  // Red Base (Bottom-Right)
        ];

        const TICK_RATE = 60;             // 60 ticks per second
        const TICK_INTERVAL = 1000 / TICK_RATE;
        const CANNON_COOLDOWN = 500;      // 500ms between shots
        const MISSILE_SPEED = 10;         // Units per tick
        const MISSILE_DAMAGE = 10;        // Damage per hit
        const SPLASH_RADIUS = 30;         // Explosion splash radius
        const MAX_SPEED = 100;            // Maximum robot speed
        const ROBOT_SCALE = 4;             // Visual scale multiplier for bigger robots
        const ROBOT_COLORS = [0x007bff, 0xff4136]; // Blue vs Red

        // Sensor ranges
        const SCAN_RANGE = 400;            // Standard scanner range
        const LIDAR_RANGE = 600;           // Lidar: long range, narrow beam (2 degrees)
        const SONAR_RANGE = 200;           // Sonar: short range, 360 degree sweep

        // Mine settings
        const MINE_COOLDOWN = 2000;        // 2 seconds between mine drops
        const MINE_TRIGGER_RADIUS = 40;    // Proximity trigger distance
        const MINE_DAMAGE = 25;            // Damage from mine explosion
        const MAX_MINES_PER_ROBOT = 5;     // Max mines each robot can have active

        debugLog('Game constants initialized');

        // ═══════════════════════════════════════════════════════
        // Initialize Container
        // ═══════════════════════════════════════════════════════

        const appletContainer = document.getElementById('applet-root');
        if (!appletContainer) {
            throw new Error('Applet root element not found');
        }

        appletContainer.innerHTML = '';
        appletContainer.style.cssText = 'margin:0;padding:0;width:100%;height:100vh;overflow:hidden;background:#1a2e40;position:relative;';

        // Create game container
        const gameContainer = document.createElement('div');
        gameContainer.id = 'game-container';
        gameContainer.style.cssText = 'width:100%;height:100%;';
        appletContainer.appendChild(gameContainer);

        debugLog('✅ Container initialized');

        // ═══════════════════════════════════════════════════════
        // Game State
        // ═══════════════════════════════════════════════════════

        const GameState = {
            MENU: 'MENU',
            PLAYING: 'PLAYING',
            GAME_OVER: 'GAME_OVER'
        };

        let currentState = GameState.MENU;
        let gameLoop = null;
        let scene, camera, renderer;
        let robots = [];
        let missiles = [];
        let obstacles = []; // v2.1 Obstacles
        let explosions = [];
        let battleStats = {
            shotsFired: [0, 0],
            shotsHit: [0, 0],
            damageDealt: [0, 0],
            distanceTraveled: [0, 0],
            minesDropped: [0, 0],
            isDraw: false
        };

        // Initialize Session Stats (Persistent across matches)
        const sessionStats = {
            blueWins: 0,
            redWins: 0,
            draws: 0
        };

        let mines = [];      // Active mines on the field
        let debris = [];     // Death explosion debris particles

        // ═══════════════════════════════════════════════════════
        // Sound Effects System (Web Audio API)
        // ═══════════════════════════════════════════════════════

        let audioContext;
        let masterGain;
        let recordingDest; // Node to capture audio for stream
        let engineOscillators = {};

        function initAudio() {
            if (audioContext) return;
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            audioContext = new AudioContext();

            // Create a Master Gain to control volume
            masterGain = audioContext.createGain();
            masterGain.gain.value = 0.5;
            masterGain.connect(audioContext.destination);

            // Create a Destination for Recording (Stream)
            recordingDest = audioContext.createMediaStreamDestination();
            masterGain.connect(recordingDest); // Connect output to recorder too

            debugLog('Audio initialized (Recording Ready)');
            if (audioContext.state === 'suspended') {
                audioContext.resume().then(() => debugLog('Audio Context Resumed'));
            }
        }

        function playSound(type) {
            // Helper logic if needed, but we use specific functions
        }

        function playShootSound() {
            if (!audioContext) return;
            const osc = audioContext.createOscillator();
            const gain = audioContext.createGain();
            osc.connect(gain);
            gain.connect(masterGain); // Connect to Master (which goes to speakers + recorder)
            osc.type = 'square';
            osc.frequency.setValueAtTime(440, audioContext.currentTime);
            osc.frequency.exponentialRampToValueAtTime(110, audioContext.currentTime + 0.1);
            gain.gain.setValueAtTime(0.3, audioContext.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            osc.start(audioContext.currentTime);
            osc.stop(audioContext.currentTime + 0.1);
        }

        function playExplosionSound() {
            if (!audioContext) return;
            // Noise buffer for explosion
            const duration = 0.5;
            const bufferSize = audioContext.sampleRate * duration;
            const buffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate);
            const data = buffer.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) {
                data[i] = Math.random() * 2 - 1;
            }
            const noise = audioContext.createBufferSource();
            noise.buffer = buffer;
            const gain = audioContext.createGain();
            noise.connect(gain);
            gain.connect(masterGain);
            gain.gain.setValueAtTime(0.5, audioContext.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);
            noise.start(audioContext.currentTime);
        }

        function playDamageSound() {
            if (!audioContext) return;
            const osc = audioContext.createOscillator();
            const gain = audioContext.createGain();
            osc.connect(gain);
            gain.connect(masterGain);
            osc.type = 'square';
            osc.frequency.setValueAtTime(150, audioContext.currentTime);
            osc.frequency.setValueAtTime(100, audioContext.currentTime + 0.05);
            osc.frequency.setValueAtTime(80, audioContext.currentTime + 0.1);
            gain.gain.setValueAtTime(0.2, audioContext.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            osc.start(audioContext.currentTime);
            osc.stop(audioContext.currentTime + 0.2);
        }

        function playVictorySound() {
            if (!audioContext) return;
            // Victory fanfare - ascending notes
            const notes = [262, 330, 392, 523]; // C E G C
            notes.forEach((freq, i) => {
                const osc = audioContext.createOscillator();
                const gain = audioContext.createGain();
                osc.connect(gain);
                gain.connect(masterGain);
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(freq, audioContext.currentTime + i * 0.15);
                gain.gain.setValueAtTime(0.3, audioContext.currentTime + i * 0.15);
                gain.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + i * 0.15 + 0.3);
                osc.start(audioContext.currentTime + i * 0.15);
                osc.stop(audioContext.currentTime + i * 0.15 + 0.3);
            });
        }

        function startEngineSound(robotId) {
            if (!audioContext || engineOscillators[robotId]) return;
            const osc = audioContext.createOscillator();
            const gain = audioContext.createGain();
            osc.connect(gain);
            gain.connect(masterGain);
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(30 + robotId * 5, audioContext.currentTime); // Slightly different pitch per robot
            gain.gain.setValueAtTime(0.05, audioContext.currentTime);
            osc.start();
            engineOscillators[robotId] = { osc, gain };
        }

        function updateEngineSound(robotId, speed) {
            if (!engineOscillators[robotId]) return;
            const { osc, gain } = engineOscillators[robotId];
            // Vary frequency and volume based on speed
            const baseFreq = 30 + robotId * 5;
            osc.frequency.setValueAtTime(baseFreq + speed * 0.5, audioContext.currentTime);
            gain.gain.setValueAtTime(0.02 + speed * 0.001, audioContext.currentTime);
        }

        function stopEngineSound(robotId) {
            if (!engineOscillators[robotId]) return;
            engineOscillators[robotId].osc.stop();
            engineOscillators[robotId] = null;
        }

        function stopAllEngineSounds() {
            stopEngineSound(0);
            stopEngineSound(1);
        }

        // ═══════════════════════════════════════════════════════
        // Video Recording System (for X.com sharing)
        // ═══════════════════════════════════════════════════════

        let mediaRecorder = null;
        let recordedChunks = [];
        let recordedBlob = null;
        let isRecording = false;

        function startRecording() {
            if (!renderer || !renderer.domElement) {
                debugLog('Cannot record: renderer not ready');
                return false;
            }

            try {
                const canvas = renderer.domElement;
                const canvasStream = canvas.captureStream(30); // 30 fps

                // Add Audio Track if available!
                let finalStream = canvasStream;
                if (recordingDest && recordingDest.stream.getAudioTracks().length > 0) {
                    debugLog('Adding audio track to recording...');
                    finalStream = new MediaStream([
                        ...canvasStream.getVideoTracks(),
                        ...recordingDest.stream.getAudioTracks()
                    ]);
                } else {
                    debugLog('No audio track available for recording.');
                }

                // Try WebM first (best support), fallback to MP4
                const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
                    ? 'video/webm;codecs=vp9'
                    : MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
                        ? 'video/webm;codecs=vp8'
                        : MediaRecorder.isTypeSupported('video/webm')
                            ? 'video/webm'
                            : 'video/mp4';

                debugLog('Using mime type: ' + mimeType);

                mediaRecorder = new MediaRecorder(finalStream, {
                    mimeType: mimeType,
                    videoBitsPerSecond: 2500000 // 2.5 Mbps for good quality
                });

                recordedChunks = [];
                recordedBlob = null;

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data && event.data.size > 0) {
                        recordedChunks.push(event.data);
                        debugLog('Recorded chunk: ' + (event.data.size / 1024).toFixed(1) + ' KB');
                    }
                };

                mediaRecorder.onstop = () => {
                    debugLog('MediaRecorder stopped. Chunks: ' + recordedChunks.length);
                    if (recordedChunks.length === 0) {
                        debugLog('ERROR: No recorded chunks!');
                        return;
                    }
                    recordedBlob = new Blob(recordedChunks, { type: mimeType });
                    debugLog(`Recording saved: ${(recordedBlob.size / 1024 / 1024).toFixed(2)} MB`);
                    isRecording = false;
                    updateRecordingIndicator();

                    // AUTO-UPLOAD: Trigger save immediately upon game end
                    setTimeout(downloadRecording, 500);
                };

                mediaRecorder.onerror = (event) => {
                    debugLog('MediaRecorder error: ' + event.error);
                    console.error('MediaRecorder error:', event);
                };

                // Start continuous recording (no timeslice for better container integrity)
                mediaRecorder.start();
                isRecording = true;
                updateRecordingIndicator();
                debugLog('🔴 Recording started (continuous mode)');
                return true;
            } catch (e) {
                console.error('Recording error:', e);
                debugLog('Recording failed: ' + e.message);
                alert('Recording Failed to Start: ' + e.message); // Explicit alert
                return false;
            }
        }

        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                debugLog('Stopping MediaRecorder (state: ' + mediaRecorder.state + ')');
                // Request any remaining data before stopping
                try {
                    mediaRecorder.requestData();
                } catch (e) {
                    debugLog('requestData failed: ' + e.message);
                }
                // Small delay to ensure data is captured
                setTimeout(() => {
                    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                        mediaRecorder.stop();
                        debugLog('⏹️ Recording stopped');
                    }
                }, 100);
            }
        }

        function downloadRecording() {
            console.log('Download requested, recordedBlob:', recordedBlob);

            if (!recordedBlob) {
                // If currently recording, stop it first
                if (isRecording && mediaRecorder && mediaRecorder.state === 'recording') {
                    mediaRecorder.stop();
                    debugLog('Stopping recording for download...');
                    // Wait for onstop event
                    setTimeout(downloadRecording, 200);
                    return;
                }

                // Check if we have chunks from a finished recording
                if (recordedChunks.length > 0) {
                    const mimeType = 'video/webm';
                    recordedBlob = new Blob(recordedChunks, { type: mimeType });
                } else {
                    alert('No recording found. Play a game first!');
                    return;
                }
            }
            const winner = robots[0].damage >= 100 ? 'Red' : 'Blue';
            const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
            const filename = 'AIRobotWars_' + winner + 'Wins_' + timestamp + '.webm';

            const formData = new FormData();
            formData.append('recording', recordedBlob, filename);
            formData.append('filename', filename);

            debugLog('Saving to server folder...');

            fetch('/api/upload_recording/', {
                method: 'POST',
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        debugLog('✅ Saved: ' + filename);
                        alert('Recording saved to server:\n' + data.path);
                    } else {
                        debugLog('❌ Error: ' + data.message);
                        alert('Save failed: ' + data.message);
                    }
                })
                .catch(e => {
                    debugLog('❌ Upload Failed: ' + e);
                    console.error(e);
                });
        }

        function updateRecordingIndicator() {
            const indicator = document.getElementById('recording-indicator');
            if (indicator) {
                indicator.style.display = isRecording ? 'flex' : 'none';
            }
        }

        // ═══════════════════════════════════════════════════════
        // Robot Class
        // ═══════════════════════════════════════════════════════

        class Robot {
            constructor(id, x, y, color, controlScript) {
                this.id = id;
                this.x = x;
                this.y = y;
                this.heading = id === 0 ? 0 : 180; // Face each other
                this.speed = 0;
                this.targetSpeed = 0;
                this.targetHeading = this.heading;
                this.damage = 0;
                this.energy = MAX_ENERGY;     // Battery level
                this.color = color;
                this.lastCannonTime = 0;
                this.lastMineTime = 0;
                this.turretAngle = 0;         // Turret angle relative to body
                this.targetTurretAngle = 0;   // Where turret is trying to aim
                this.controlScript = controlScript;
                this.mesh = null;
                this.turretMesh = null;
                this.scanMesh = null;
                this.lastScanAngle = 0;
                this.lastScanResolution = 10;
                this.pauseTicks = 0; // v2.3 Timer for PAUSE command

                // Create 3D mesh
                this.createMesh();
            }

            createMesh() {
                // Robot body - SAUCER (Cylinder)
                const bodyGeometry = new THREE.CylinderGeometry(
                    ROBOT_SIZE * 0.05 * ROBOT_SCALE, // Top Radius
                    ROBOT_SIZE * 0.05 * ROBOT_SCALE, // Bottom Radius
                    ROBOT_SIZE * 0.02 * ROBOT_SCALE, // Height
                    32 // Radial Segments (smooth)
                );

                // Silver Metal Material
                const bodyMaterial = new THREE.MeshStandardMaterial({
                    color: 0xcccccc, // Silver
                    roughness: 0.2,  // Shiny
                    metalness: 0.8  // Metallic
                });

                // Mix in team color (emissive ring or top?)
                // Let's make the robot silver, but add a colored glowing ring on top

                this.mesh = new THREE.Mesh(bodyGeometry, bodyMaterial);
                this.mesh.castShadow = true;

                // Identification Ring (Team Color)
                const ringGeo = new THREE.RingGeometry(ROBOT_SIZE * 0.02 * ROBOT_SCALE, ROBOT_SIZE * 0.04 * ROBOT_SCALE, 32);
                const ringMat = new THREE.MeshBasicMaterial({ color: this.color, side: THREE.DoubleSide });
                const ring = new THREE.Mesh(ringGeo, ringMat);
                ring.rotation.x = -Math.PI / 2;
                ring.position.y = ROBOT_SIZE * 0.011 * ROBOT_SCALE; // Just above surface
                this.mesh.add(ring);

                // Cannon (Small opening or blaster on front)
                const blasterGeo = new THREE.BoxGeometry(
                    ROBOT_SIZE * 0.01 * ROBOT_SCALE,
                    ROBOT_SIZE * 0.01 * ROBOT_SCALE,
                    ROBOT_SIZE * 0.02 * ROBOT_SCALE
                );
                const blasterMat = new THREE.MeshStandardMaterial({ color: 0x111111 });
                const blaster = new THREE.Mesh(blasterGeo, blasterMat);
                blaster.position.set(0, 0, ROBOT_SIZE * 0.04 * ROBOT_SCALE); // Front edge
                this.mesh.add(blaster);

                // Scan cone
                const scanGeometry = new THREE.ConeGeometry(
                    ARENA_SIZE * 0.03,
                    ARENA_SIZE * 0.5,
                    8
                );
                const scanMaterial = new THREE.MeshBasicMaterial({
                    color: this.color,
                    transparent: true,
                    opacity: 0.15,
                    side: THREE.DoubleSide
                });
                this.scanMesh = new THREE.Mesh(scanGeometry, scanMaterial);
                this.scanMesh.visible = false;
                this.scanMesh.rotation.x = Math.PI / 2;
                this.mesh.add(this.scanMesh);

                this.updatePosition();

                // 3D UI Bars
                this.createUI();

                scene.add(this.mesh);
            }

            createUI() {
                // UI container above robot
                this.uiMesh = new THREE.Group();
                this.uiMesh.position.y = 2.0; // Float above
                this.uiMesh.rotation.y = Math.PI / 4; // Angled to camera usually
                this.mesh.add(this.uiMesh);

                // Health Bar Back
                const barWidth = 1.5;
                const barHeight = 0.2;
                const backGeo = new THREE.PlaneGeometry(barWidth, barHeight);
                const backMat = new THREE.MeshBasicMaterial({ color: 0x333333 });

                // HP Bar
                const hpBack = new THREE.Mesh(backGeo, backMat);
                hpBack.position.y = 0.3;
                this.uiMesh.add(hpBack);

                const hpFrontGeo = new THREE.PlaneGeometry(barWidth, barHeight);
                hpFrontGeo.translate(barWidth / 2, 0, 0); // Anchor left
                const hpFrontMat = new THREE.MeshBasicMaterial({ color: 0x22c55e });
                this.hpBar = new THREE.Mesh(hpFrontGeo, hpFrontMat);
                this.hpBar.position.x = -barWidth / 2;
                this.hpBar.position.y = 0.3;
                this.hpBar.position.z = 0.01; // Front
                this.uiMesh.add(this.hpBar);

                // Energy Bar
                const enBack = new THREE.Mesh(backGeo, backMat);
                enBack.position.y = 0;
                this.uiMesh.add(enBack);

                const enFrontGeo = new THREE.PlaneGeometry(barWidth, barHeight);
                enFrontGeo.translate(barWidth / 2, 0, 0); // Anchor left
                const enFrontMat = new THREE.MeshBasicMaterial({ color: 0x3b82f6 });
                this.enBar = new THREE.Mesh(enFrontGeo, enFrontMat);
                this.enBar.position.x = -barWidth / 2;
                this.enBar.position.y = 0;
                this.enBar.position.z = 0.01;
                this.uiMesh.add(this.enBar);
            }

            updateUI() {
                // Billboard effect (face camera)
                this.uiMesh.lookAt(camera.position);

                // Update scales
                const hpScale = Math.max(0, (100 - this.damage) / 100);
                this.hpBar.scale.x = hpScale;
                this.hpBar.material.color.setHex(hpScale < 0.3 ? 0xef4444 : 0x22c55e);

                const enScale = Math.max(0, this.energy / MAX_ENERGY);
                this.enBar.scale.x = enScale;
                this.enBar.material.color.setHex(enScale < 0.2 ? 0xf59e0b : 0x3b82f6);
            }

            updatePosition() {
                // Convert game coordinates to 3D world coordinates
                // Arena center is at (0,0), scale to world units
                const scale = 0.1; // 1000 arena units = 100 world units
                this.mesh.position.x = (this.x - ARENA_SIZE / 2) * scale;
                this.mesh.position.z = (this.y - ARENA_SIZE / 2) * scale;
                this.mesh.position.y = 0.5;
                this.mesh.rotation.y = -this.heading * (Math.PI / 180);
            }

            // Robot API methods
            scan(degree, resolution) {
                // Drain energy for scanning
                this.energy -= ENERGY_DRAIN_SCAN;

                resolution = Math.max(1, Math.min(40, resolution));
                const startAngle = (this.heading + degree - resolution / 2) % 360;
                const endAngle = (this.heading + degree + resolution / 2) % 360;

                // Update scan visualization
                this.lastScanAngle = degree;
                this.lastScanResolution = resolution;
                this.showScan(degree, resolution);

                let closestDistance = 0;

                for (const robot of robots) {
                    if (robot.id === this.id) continue;

                    const dx = robot.x - this.x;
                    const dy = robot.y - this.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    let angle = Math.atan2(dy, dx) * (180 / Math.PI);
                    angle = (angle + 360) % 360;

                    // Check if angle is within scan arc
                    let inArc = false;
                    if (startAngle <= endAngle) {
                        inArc = angle >= startAngle && angle <= endAngle;
                    } else {
                        inArc = angle >= startAngle || angle <= endAngle;
                    }

                    if (inArc) {
                        // Check if within scan range
                        if (distance <= SCAN_RANGE) {
                            if (closestDistance === 0 || distance < closestDistance) {
                                closestDistance = distance;
                            }
                        }
                    }
                }

                return Math.floor(closestDistance);
            }

            // LIDAR: Narrow beam (2 degrees), long range (600)
            lidar(degree) {
                const scanAngle = (this.heading + degree + 360) % 360;

                // Visualize the beam (narrow)
                this.showScan(degree, 2);

                let closestDistance = 0;

                for (const robot of robots) {
                    if (robot.id === this.id) continue;

                    const dx = robot.x - this.x;
                    const dy = robot.y - this.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance > LIDAR_RANGE) continue; // Optimization

                    // Check if obstacles block line of sight
                    let blocked = false;
                    for (const obs of obstacles) {
                        // Simple check: Is obstacle closer and generally in the way?
                        // Improve with ray check later if needed
                        const dObs = Math.sqrt((obs.x - this.x) ** 2 + (obs.y - this.y) ** 2);
                        if (dObs < distance && dObs < LIDAR_RANGE) {
                            // Check if angle to obstacle is close to angle to robot
                            const angleToObs = Math.atan2(obs.y - this.y, obs.x - this.x) * (180 / Math.PI);
                            const angleToBot = Math.atan2(dy, dx) * (180 / Math.PI);
                            let diff = Math.abs(angleToObs - angleToBot);
                            if (diff > 180) diff = 360 - diff;

                            const obsAngularWidth = (Math.atan2(obs.size / 2, dObs) * (180 / Math.PI)) * 2;

                            if (diff < obsAngularWidth) {
                                blocked = true;
                                break;
                            }
                        }
                    }
                    if (blocked) continue; // Can't see robot through obstacle

                    let angle = Math.atan2(dy, dx) * (180 / Math.PI);
                    angle = (angle + 360) % 360;

                    // Very narrow beam - 2 degrees
                    const angleDiff = Math.abs(angle - scanAngle);
                    const normalizedDiff = angleDiff > 180 ? 360 - angleDiff : angleDiff;

                    if (normalizedDiff <= 1) {
                        if (closestDistance === 0 || distance < closestDistance) {
                            closestDistance = distance;
                        }
                    }
                }

                return Math.floor(closestDistance);
            }

            // SONAR: 360 degree sweep, short range (200), returns direction to closest enemy
            sonar() {
                let closestDistance = SONAR_RANGE + 1;
                let closestAngle = -1;

                for (const robot of robots) {
                    if (robot.id === this.id) continue;

                    const dx = robot.x - this.x;
                    const dy = robot.y - this.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance <= SONAR_RANGE && distance < closestDistance) {
                        closestDistance = distance;
                        closestAngle = Math.atan2(dy, dx) * (180 / Math.PI);
                        closestAngle = (closestAngle + 360) % 360;
                    }
                }

                // Returns object with angle and distance, or null if nothing found
                if (closestAngle >= 0) {
                    return { angle: Math.floor(closestAngle), distance: Math.floor(closestDistance) };
                }
                return null;
            }

            cannon(degree, distance) {
                const now = Date.now();
                if (now - this.lastCannonTime < CANNON_COOLDOWN) {
                    return false; // Still cooling down
                }

                // Check energy
                if (this.energy < ENERGY_DRAIN_FIRE) {
                    return false; // Not enough energy
                }

                // Set turret to aim at target (Visual only, aiming is instant for Saucers now)
                this.targetTurretAngle = degree;

                // SAUCER MOD: No turret wait. We assume the "gun" inside the saucer rotates instantly or the saucer rotates.
                // For gameplay flow, we'll allow instant firing at the requested angle relative to heading.

                // Drain energy and fire
                this.energy -= ENERGY_DRAIN_FIRE;
                this.lastCannonTime = now;
                battleStats.shotsFired[this.id]++;

                // Fire from requested angle relative to heading
                const fireAngle = (this.heading + degree) * (Math.PI / 180);
                const targetX = this.x + Math.cos(fireAngle) * distance;
                const targetY = this.y + Math.sin(fireAngle) * distance;

                missiles.push({
                    ownerId: this.id,
                    x: this.x,
                    y: this.y,
                    targetX: Math.max(0, Math.min(ARENA_SIZE, targetX)),
                    targetY: Math.max(0, Math.min(ARENA_SIZE, targetY)),
                    angle: fireAngle,
                    totalDistance: distance,
                    traveledDistance: 0,
                    mesh: this.createMissileMesh()
                });

                // Play shoot sound
                playShootSound();

                return true;
            }

            aimTurret(degree) {
                this.targetTurretAngle = degree;
            }

            createMissileMesh() {
                const geometry = new THREE.SphereGeometry(0.15, 8, 8);
                const material = new THREE.MeshBasicMaterial({ color: 0xffff00 });
                const mesh = new THREE.Mesh(geometry, material);
                scene.add(mesh);
                return mesh;
            }

            drive(degree, speed) {
                this.targetHeading = (degree + 360) % 360;
                this.targetSpeed = Math.max(0, Math.min(MAX_SPEED, speed));
            }

            // Status methods
            getDamage() { return this.damage; }
            getEnergy() { return this.energy; }
            getLocX() { return this.x; }
            getLocY() { return this.y; }
            getSpeed() { return this.speed; }

            showScan(degree, resolution) {
                this.scanMesh.visible = true;
                const angle = degree * (Math.PI / 180);
                this.scanMesh.rotation.y = -angle;

                // Scale cone based on resolution
                const scale = resolution / 20;
                this.scanMesh.scale.x = scale;

                // Hide after short delay
                setTimeout(() => {
                    this.scanMesh.visible = false;
                }, 100);
            }

            dropMine() {
                const now = Date.now();
                if (now - this.lastMineTime < MINE_COOLDOWN) {
                    return false; // Still cooling down
                }

                // Check energy
                if (this.energy < ENERGY_DRAIN_MINE) {
                    return false; // Not enough energy
                }

                // Check max mines
                const myMines = mines.filter(m => m.ownerId === this.id);
                if (myMines.length >= MAX_MINES_PER_ROBOT) {
                    return false; // Too many mines
                }

                // Drain energy
                this.energy -= ENERGY_DRAIN_MINE;
                this.lastMineTime = now;
                battleStats.minesDropped[this.id]++;

                // Create mine mesh
                const scale = 0.1;
                const geometry = new THREE.CylinderGeometry(0.3, 0.4, 0.15, 8);
                const material = new THREE.MeshStandardMaterial({
                    color: this.color,
                    emissive: this.color,
                    emissiveIntensity: 0.3
                });
                const mesh = new THREE.Mesh(geometry, material);
                mesh.position.x = (this.x - ARENA_SIZE / 2) * scale;
                mesh.position.z = (this.y - ARENA_SIZE / 2) * scale;
                mesh.position.y = 0.1;
                scene.add(mesh);

                mines.push({
                    ownerId: this.id,
                    x: this.x,
                    y: this.y,
                    mesh: mesh,
                    armed: false,
                    armTime: now + 500 // Arm after 500ms so you can escape
                });

                debugLog('Mine dropped by Robot ' + this.id);
                return true;
            }

            update() {
                // If out of energy, stop!
                if (this.energy <= 0) {
                    this.targetSpeed = 0;
                }

                // Gradually adjust heading toward target
                let headingDiff = this.targetHeading - this.heading;
                if (headingDiff > 180) headingDiff -= 360;
                if (headingDiff < -180) headingDiff += 360;

                // Turn rate decreases with speed
                const turnRate = Math.max(1, 10 - this.speed * 0.08);
                if (Math.abs(headingDiff) > turnRate) {
                    this.heading += Math.sign(headingDiff) * turnRate;
                } else {
                    this.heading = this.targetHeading;
                }
                this.heading = (this.heading + 360) % 360;

                this.heading = (this.heading + 360) % 360;

                // Turret Logic Removed (v2.1) - Guns fixed forward
                this.turretAngle = 0; // Always 0 relative to body

                // Base Recharge Mechanics (v2.0)
                const base = BASES[this.id];
                const dx = this.x - base.x;
                const dy = this.y - base.y;
                if (Math.sqrt(dx * dx + dy * dy) < BASE_RADIUS) {
                    // In base! Recharge and Repair.
                    this.energy = Math.min(MAX_ENERGY, this.energy + BASE_RECHARGE_RATE);
                    this.damage = Math.max(0, this.damage - BASE_REPAIR_RATE);
                }

                // Update health/energy UI (3D)
                if (this.uiMesh) this.updateUI();

                // Update turret mesh rotation
                if (this.turretMesh) {
                    this.turretMesh.rotation.y = -this.turretAngle * (Math.PI / 180);
                }

                // Gradually adjust speed
                if (this.speed < this.targetSpeed) {
                    this.speed = Math.min(this.targetSpeed, this.speed + 2);
                } else if (this.speed > this.targetSpeed) {
                    this.speed = Math.max(this.targetSpeed, this.speed - 2);
                }

                // Move robot
                if (this.speed > 0) {
                    const radians = this.heading * (Math.PI / 180);
                    const dx = Math.cos(radians) * this.speed * 0.1;
                    const dy = Math.sin(radians) * this.speed * 0.1;

                    this.x += dx;
                    this.y += dy;

                    battleStats.distanceTraveled[this.id] += Math.sqrt(dx * dx + dy * dy);

                    // Wall collision (just blocks, minimal damage)
                    if (this.x < ROBOT_SIZE) { this.x = ROBOT_SIZE; this.damage += 0.1; }
                    if (this.x > ARENA_SIZE - ROBOT_SIZE) { this.x = ARENA_SIZE - ROBOT_SIZE; this.damage += 0.1; }
                    if (this.y < ROBOT_SIZE) { this.y = ROBOT_SIZE; this.damage += 0.1; }
                    if (this.y > ARENA_SIZE - ROBOT_SIZE) { this.y = ARENA_SIZE - ROBOT_SIZE; this.damage += 0.1; }
                }

                // Obstacle Collision (v2.1)
                for (const obs of obstacles) {
                    const dx = obs.x - this.x;
                    const dy = obs.y - this.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    // Approximate collision (Circle vs Circle/Box)
                    // Treat obstacles as circles of radius size/1.5 for simplicity
                    const minDist = ROBOT_SIZE + obs.size * 0.6;

                    if (dist < minDist) {
                        // Bounce/Slide
                        const overlap = minDist - dist;
                        const nx = dx / dist;
                        const ny = dy / dist;

                        this.x -= nx * overlap;
                        this.y -= ny * overlap;
                        // Reduce speed on hit
                        this.speed *= 0.5;
                    }
                }

                // Robot collision
                for (const other of robots) {
                    if (other.id === this.id) continue;
                    const dx = other.x - this.x;
                    const dy = other.y - this.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < ROBOT_SIZE * 2) {
                        // Push apart
                        const overlap = ROBOT_SIZE * 2 - dist;
                        const nx = dx / dist;
                        const ny = dy / dist;
                        this.x -= nx * overlap / 2;
                        this.y -= ny * overlap / 2;
                        other.x += nx * overlap / 2;
                        other.y += ny * overlap / 2;
                        // Damage from collision
                        this.damage += 0.5;
                        other.damage += 0.5;
                    }
                }

                // Update engine sound based on speed
                updateEngineSound(this.id, this.speed);

                // Drain energy (idle drains less, moving drains more)
                this.energy -= ENERGY_DRAIN_IDLE;
                if (this.speed > 0) {
                    this.energy -= this.speed * ENERGY_DRAIN_MOVE;
                }
                this.energy = Math.max(0, this.energy);

                this.updatePosition();
            }

            executeAI() {
                if (this.damage >= 100) return;

                // Handle PAUSE command
                if (this.pauseTicks > 0) {
                    this.pauseTicks--;
                    return; // Skip AI execution this tick
                }

                if (this.energy <= 0) return; // Out of energy, can't execute AI

                // Create API object for AI script
                const api = {
                    // Variables (approximate directly accessible values)
                    HEALTH: Math.max(0, 100 - this.damage),
                    ENERGY: this.energy,
                    HOME: BASES[this.id],
                    ENEMY: BASES[(this.id + 1) % 2],

                    // Commands
                    PAUSE: (ticks) => { this.pauseTicks = ticks; }, // Logic: stop for N ticks

                    // Standard API
                    scan: (deg, res) => this.scan(deg, res),
                    lidar: (deg) => this.lidar(deg),
                    sonar: () => this.sonar(),
                    cannon: (deg, dist) => this.cannon(deg, dist),
                    dropMine: () => this.dropMine(),
                    drive: (deg, spd) => this.drive(deg, spd),
                    damage: () => this.getDamage(),
                    energy: () => this.getEnergy(),
                    loc_x: () => this.getLocX(),
                    loc_y: () => this.getLocY(),
                    speed: () => this.getSpeed(),
                    heading: () => this.heading, // Expose heading
                    log: (msg) => debugLog(`🤖 Bot ${this.id + 1}: ${msg}`), // Expose logging
                    // Bases (v2.0)
                    base: () => BASES[this.id],
                    enemy_base: () => BASES[(this.id + 1) % 2]
                };

                try {
                    this.controlScript(api);
                } catch (e) {
                    console.error(`Robot ${this.id} AI error:`, e);
                    // Automatic loss for crashing the interpreter
                    this.damage = 100;
                    debugLog(`❌ ROBOT ${this.id + 1} SCRIPT CRASHED! Auto-Destruct initiated.`);
                    debugLog(`Error: ${e.message}`);
                }
            }

            destroy() {
                if (this.mesh) {
                    scene.remove(this.mesh);
                }
            }
        }

        // ═══════════════════════════════════════════════════════
        // AI Scripts (Hardcoded for V1)
        // ═══════════════════════════════════════════════════════

        // Aggressive Hunter AI - actively seeks and destroys
        function aggressiveAI(api) {
            const myX = api.loc_x();
            const myY = api.loc_y();

            // Scan in current direction
            let range = api.scan(0, 10);

            // If nothing found, rotate scan
            if (range === 0) {
                for (let angle = 0; angle < 360; angle += 20) {
                    range = api.scan(angle, 10);
                    if (range > 0) {
                        api.drive(angle, 80);
                        if (range < 200) {
                            api.cannon(angle, range);
                        }
                        return;
                    }
                }
                // Random movement if nothing found
                api.drive(Math.random() * 360, 50);
            } else {
                // Target found - attack!
                api.drive(0, 60);
                api.cannon(0, range);
            }
        }

        // Defensive Sniper AI - keeps distance, precise shots
        function defensiveAI(api) {
            const myX = api.loc_x();
            const myY = api.loc_y();
            const damage = api.damage();

            // Stay near center but move unpredictably
            const centerX = 500;
            const centerY = 500;
            const distFromCenter = Math.sqrt((myX - centerX) ** 2 + (myY - centerY) ** 2);

            // Scan all directions
            for (let angle = 0; angle < 360; angle += 15) {
                const range = api.scan(angle, 8);
                if (range > 0) {
                    // Fire at detected enemy
                    api.cannon(angle, range);

                    // If too close, back away
                    if (range < 300) {
                        const retreatAngle = (angle + 180) % 360;
                        api.drive(retreatAngle, 70);
                    } else {
                        // Circle strafe
                        api.drive((angle + 90) % 360, 40);
                    }
                    return;
                }
            }

            // If too far from center, move back
            if (distFromCenter > 300) {
                const angleToCenter = Math.atan2(centerY - myY, centerX - myX) * (180 / Math.PI);
                api.drive(angleToCenter, 30);
            } else {
                // Random patrol
                api.drive(Math.random() * 360, 25);
            }
        }

        // ═══════════════════════════════════════════════════════
        // Custom Script System
        // ═══════════════════════════════════════════════════════

        // Default script templates

        const DEFAULT_SCRIPT_1 = `
        // Blue Robot (The Hunter)
        // Uses Sonar for close combat and PAUSE to recharge
        function robotScript(api) {
            const myX = api.loc_x();
            const myY = api.loc_y();
            const home = api.HOME;

            // 1. Survival: Go Home if low energy or high damage
            // Max Energy is 2500, so < 500 is very low (~20%)
            if (api.ENERGY < 500 || api.HEALTH < 40) {
                const dx = home.x - myX;
                const dy = home.y - myY;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 80) {
                    api.drive(0, 0); // Stop
                    api.PAUSE(60);   // Power Nap (1 sec)
                    return;
                }

                const angleToHome = Math.atan2(dy, dx) * (180 / Math.PI);
                api.drive(angleToHome, 100);
                return;
            }

            // 2. Combat: Check Sonar (Cheap & Fast)
            const target = api.sonar();
            if (target) {
                api.cannon(target.angle, target.distance);
                if (target.distance < 200) api.dropMine();
                // Strafe
                api.drive(target.angle + 90, 80);
                return;
            }

            // 3. Hunt: Move towards enemy base but keep distance
            const enemyBase = api.ENEMY;
            const distToEnemy = Math.sqrt((myX - enemyBase.x) ** 2 + (myY - enemyBase.y) ** 2);

            if (distToEnemy > 600) {
                const angle = Math.atan2(enemyBase.y - myY, enemyBase.x - myX) * (180 / Math.PI);
                api.drive(angle, 60);
            } else {
                // Circle behavior
                api.drive(api.heading() + 2, 40);
                // Random Lidar Potshots
                if (Math.random() < 0.1) {
                    const scanAngle = (api.heading() - 45 + Math.random() * 90) % 360;
                    const range = api.lidar(scanAngle);
                    if (range > 0) api.cannon(scanAngle, range);
                }
            }
        } `;

        const DEFAULT_SCRIPT_2 = `
        // Red Robot (The Sniper)
        // Camps near walls and uses Lidar. Recharges aggressively.
        function robotScript(api) {
            // 1. Check Energy First
            if (api.ENERGY < 800) {
                const home = api.HOME;
                const dx = home.x - api.loc_x();
                const dy = home.y - api.loc_y();
                if (Math.sqrt(dx * dx + dy * dy) < 80) {
                    api.PAUSE(30); // Quick recharge
                    return;
                }
                const angle = Math.atan2(dy, dx) * (180 / Math.PI);
                api.drive(angle, 100);
                return;
            }

            // 2. Long Range Scan (Lidar)
            // Scan a 60 degree arc in front
            const heading = api.heading();
            for (let i = -30; i <= 30; i += 5) {
                const angle = (heading + i + 360) % 360;
                const range = api.lidar(angle);
                if (range > 0 && range < 600) {
                    api.cannon(angle, range);
                    return;
                }
            }

            // 3. Move unpredictably
            if (Math.random() < 0.05) {
                // Change direction
                const dest = {
                    x: 100 + Math.random() * 800,
                    y: 100 + Math.random() * 800
                };
                const angle = Math.atan2(dest.y - api.loc_y(), dest.x - api.loc_x()) * (180 / Math.PI);
                api.drive(angle, 40);
            }
        } `;

        const SCRIPT_GUIDE = `=== AI ROBOT WARS SCRIPT GUIDE(v2.3) ===

            // NEW IN V2.3:
            // - api.PAUSE(ticks): Sleep/Recharge (60 ticks = 1s)
            // - api.HOME / api.ENEMY: Base coordinates {x,y}
            // - api.HEALTH / api.ENERGY: Direct variables

            function robotScript(api) {
                // 1. Recharge if low (Max Energy = 2500)
                if (api.ENERGY < 750) {
                    api.drive(angleTo(api.HOME), 100);
                    if (distTo(api.HOME) < 80) api.PAUSE(60);
                    return;
                }

                // 2. Scan & Attack
                let target = api.sonar();
                if (target) {
                    api.cannon(target.angle, target.distance);
                } else {
                    // Patrol...
                }
            }

                // Helper functions:
                // angleTo(target)
                // distTo(target)
                `;

        // Custom scripts storage
        let customScripts = {
            robot1: DEFAULT_SCRIPT_1,
            robot2: DEFAULT_SCRIPT_2
        };
        // Initialize active scripts by compiling defaults (Synchronous)
        // Helper to safely compile or return a dummy
        function safeCompile(code) {
            const res = compileScript(code);
            return res.success ? res.fn : function (api) { };
        }

        let activeScripts = {
            robot1: safeCompile(DEFAULT_SCRIPT_1),
            robot2: safeCompile(DEFAULT_SCRIPT_2)
        };

        function compileScript(scriptCode) {
            try {
                // Create a function from the script text
                const wrappedCode = scriptCode + '\n; return robotScript;';
                const factory = new Function(wrappedCode);
                const scriptFn = factory();

                if (typeof scriptFn !== 'function') {
                    throw new Error('Script must define robotScript(api) function');
                }

                return { success: true, fn: scriptFn };
            } catch (e) {
                return { success: false, error: e.message };
            }
        }

        function showScriptEditor(robotNum) {
            const scriptKey = 'robot' + robotNum;

            // Create modal overlay
            const overlay = document.createElement('div');
            overlay.id = 'script-editor-overlay';
            overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:10000;display:flex;justify-content:center;align-items:center;';

            const modal = document.createElement('div');
            modal.style.cssText = 'background:#1e293b;border:2px solid #3b82f6;border-radius:10px;padding:20px;width:80%;max-width:800px;max-height:80%;display:flex;flex-direction:column;';

            modal.innerHTML = `
            <div style = "display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;" >
                    <h2 style="margin:0;color:${robotNum === 1 ? '#60a5fa' : '#f87171'};">Edit Robot ${robotNum} Script</h2>
                    <button id="close-editor" style="background:#ef4444;border:none;color:white;padding:8px 16px;border-radius:5px;cursor:pointer;font-weight:bold;">X</button>
                </div>
                <div style="display:flex;gap:15px;flex:1;overflow:hidden;">
                    <div style="flex:1;display:flex;flex-direction:column;">
                        <label style="color:#9ca3af;margin-bottom:5px;">Script Code:</label>
                        <textarea id="script-textarea" style="flex:1;background:#0f172a;border:1px solid #334155;color:#e2e8f0;font-family:monospace;font-size:12px;padding:10px;resize:none;border-radius:5px;min-height:300px;"></textarea>
                    </div>
                    <div style="width:300px;display:flex;flex-direction:column;">
                        <label style="color:#9ca3af;margin-bottom:5px;">Reference Guide:</label>
                        <pre id="script-guide" style="flex:1;background:#0f172a;border:1px solid #334155;color:#22c55e;font-family:monospace;font-size:10px;padding:10px;overflow:auto;border-radius:5px;margin:0;white-space:pre-wrap;"></pre>
                    </div>
                </div>
                <div id="compile-status" style="margin-top:10px;padding:8px;border-radius:5px;font-size:12px;"></div>
                <div style="display:flex;gap:10px;margin-top:15px;justify-content:flex-end;">
                    <button id="reset-script" style="background:#6b7280;border:none;color:white;padding:10px 20px;border-radius:5px;cursor:pointer;">Reset to Default</button>
                    <button id="compile-script" style="background:#22c55e;border:none;color:white;padding:10px 20px;border-radius:5px;cursor:pointer;font-weight:bold;">Save & Compile</button>
                </div>
        `;

            overlay.appendChild(modal);
            document.body.appendChild(overlay);

            // Populate content
            document.getElementById('script-textarea').value = customScripts[scriptKey];
            document.getElementById('script-guide').textContent = SCRIPT_GUIDE;

            // Event handlers
            document.getElementById('close-editor').onclick = function () {
                document.body.removeChild(overlay);
            };

            document.getElementById('reset-script').onclick = function () {
                const defaultScript = robotNum === 1 ? DEFAULT_SCRIPT_1 : DEFAULT_SCRIPT_2;
                document.getElementById('script-textarea').value = defaultScript;
                document.getElementById('compile-status').innerHTML = '<span style="color:#f59e0b;">Reset to default - click Save & Compile to apply</span>';
            };

            document.getElementById('compile-script').onclick = function () {
                const code = document.getElementById('script-textarea').value;
                const result = compileScript(code);
                const statusEl = document.getElementById('compile-status');

                if (result.success) {
                    customScripts[scriptKey] = code;
                    activeScripts[scriptKey] = result.fn;
                    statusEl.innerHTML = '<span style="color:#22c55e;">Compiled successfully! Script will be used in next battle.</span>';
                    statusEl.style.background = 'rgba(34, 197, 94, 0.2)';
                } else {
                    statusEl.innerHTML = '<span style="color:#ef4444;">Compile Error: ' + result.error + '</span>';
                    statusEl.style.background = 'rgba(239, 68, 68, 0.2)';
                }
            };
        }

        // ═══════════════════════════════════════════════════════
        // Three.js Scene Setup
        // ═══════════════════════════════════════════════════════

        function initScene() {
            debugLog('Setting up Three.js scene...');

            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a2e40);

            // Orthographic camera for birds-eye view
            const aspect = window.innerWidth / window.innerHeight;
            const viewSize = 60;
            camera = new THREE.OrthographicCamera(
                -viewSize * aspect,
                viewSize * aspect,
                viewSize,
                -viewSize,
                1,
                1000
            );
            camera.position.set(0, 80, 0);
            camera.lookAt(0, 0, 0);

            // Renderer
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.shadowMap.enabled = true;
            gameContainer.appendChild(renderer.domElement);

            // Lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(20, 50, 20);
            directionalLight.castShadow = true;
            scene.add(directionalLight);

            // Arena floor
            const floorSize = ARENA_SIZE * 0.1;
            const floorGeometry = new THREE.PlaneGeometry(floorSize, floorSize, 20, 20);
            const floorMaterial = new THREE.MeshStandardMaterial({
                color: 0x334155,
                roughness: 0.9
            });
            const floor = new THREE.Mesh(floorGeometry, floorMaterial);
            floor.rotation.x = -Math.PI / 2;
            floor.receiveShadow = true;
            scene.add(floor);

            // Grid lines
            const gridHelper = new THREE.GridHelper(floorSize, 20, 0x4a5568, 0x2d3748);
            scene.add(gridHelper);

            // Bases (v2.0)
            createBaseMeshes(floorSize);

            // Obstacles (v2.1)
            createObstacles(floorSize);

            // HUD (v2.4) - Title & Win Screen attached to Camera
            createHUD();

            // Arena walls (visual only)
            const wallMaterial = new THREE.MeshStandardMaterial({
                color: 0x4a5568,
                transparent: true,
                opacity: 0.3
            });
            const wallHeight = 3;
            const wallThickness = 0.5;

            // North wall
            const northWall = new THREE.Mesh(
                new THREE.BoxGeometry(floorSize, wallHeight, wallThickness),
                wallMaterial
            );
            northWall.position.set(0, wallHeight / 2, -floorSize / 2);
            scene.add(northWall);

            // South wall
            const southWall = new THREE.Mesh(
                new THREE.BoxGeometry(floorSize, wallHeight, wallThickness),
                wallMaterial
            );
            southWall.position.set(0, wallHeight / 2, floorSize / 2);
            scene.add(southWall);

            // East wall
            const eastWall = new THREE.Mesh(
                new THREE.BoxGeometry(wallThickness, wallHeight, floorSize),
                wallMaterial
            );
            eastWall.position.set(floorSize / 2, wallHeight / 2, 0);
            scene.add(eastWall);

            // West wall
            const westWall = new THREE.Mesh(
                new THREE.BoxGeometry(wallThickness, wallHeight, floorSize),
                wallMaterial
            );
            westWall.position.set(-floorSize / 2, wallHeight / 2, 0);
            scene.add(westWall);

            debugLog('✅ Three.js scene ready');
        }

        function createBaseMeshes(floorSize) {
            const scale = 0.1;
            BASES.forEach((base, index) => {
                // Base circle
                const geometry = new THREE.CircleGeometry(BASE_RADIUS * scale, 32);
                const material = new THREE.MeshBasicMaterial({
                    color: base.color,
                    transparent: true,
                    opacity: 0.3,
                    side: THREE.DoubleSide
                });
                const circle = new THREE.Mesh(geometry, material);
                circle.rotation.x = -Math.PI / 2;
                circle.position.set(
                    (base.x - ARENA_SIZE / 2) * scale,
                    0.02, // Just above floor
                    (base.y - ARENA_SIZE / 2) * scale
                );
                scene.add(circle);

                // ENERGY text label
                const labelCanvas = document.createElement('canvas');
                labelCanvas.width = 128;
                labelCanvas.height = 32;
                const ctx = labelCanvas.getContext('2d');
                ctx.fillStyle = index === 0 ? '#60a5fa' : '#f87171';
                ctx.font = 'bold 20px monospace';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('ENERGY', 64, 16);

                const labelTex = new THREE.CanvasTexture(labelCanvas);
                const labelMat = new THREE.SpriteMaterial({ map: labelTex, transparent: true });
                const labelSprite = new THREE.Sprite(labelMat);
                labelSprite.scale.set(8, 2, 1);
                labelSprite.position.set(
                    (base.x - ARENA_SIZE / 2) * scale,
                    1.5, // Float above base
                    (base.y - ARENA_SIZE / 2) * scale
                );
                scene.add(labelSprite);
            });
        }

        function createObstacles(floorSize) {
            obstacles = []; // Reset
            const obstacleCount = Math.floor(Math.random() * 3) + 3; // 3 to 5 obstacles

            const material = new THREE.MeshStandardMaterial({
                color: 0x64748b,
                roughness: 0.7,
                metalness: 0.4
            });

            for (let i = 0; i < obstacleCount; i++) {
                let valid = false;
                let mesh, shape;
                let x, y, size;
                let attempts = 0;

                while (!valid && attempts < 50) {
                    attempts++;
                    // Random Position (keep away from edges slightly)
                    x = Math.random() * 800 + 100; // 100 to 900
                    y = Math.random() * 800 + 100;
                    size = Math.random() * 40 + 30; // 30 to 70 size

                    // Check Base Collision (CRITICAL)
                    const distBlue = Math.sqrt((x - 100) ** 2 + (y - 100) ** 2);
                    const distRed = Math.sqrt((x - 900) ** 2 + (y - 900) ** 2);

                    if (distBlue > 120 && distRed > 120) {
                        valid = true; // Far enough from bases
                        // Note: We allow clipping with walls/other obstacles for "ruined" look
                    }
                }

                if (valid) {
                    const scale = 0.1;
                    const height = 40 * scale; // 4 units high

                    if (Math.random() > 0.5) {
                        // Box (Crate)
                        const geometry = new THREE.BoxGeometry(size * scale, height, size * scale);
                        mesh = new THREE.Mesh(geometry, material);
                        shape = 'box';
                    } else {
                        // Cylinder (Pillar)
                        const geometry = new THREE.CylinderGeometry((size / 2) * scale, (size / 2) * scale, height, 16);
                        mesh = new THREE.Mesh(geometry, material);
                        shape = 'cylinder';
                    }

                    mesh.position.set(
                        (x - ARENA_SIZE / 2) * scale,
                        height / 2,
                        (y - ARENA_SIZE / 2) * scale
                    );

                    mesh.castShadow = true;
                    mesh.receiveShadow = true;
                    scene.add(mesh);

                    obstacles.push({ x, y, size, shape, mesh }); // Store for physics
                }
            }
            debugLog(`Generated ${obstacles.length} obstacles`);
        }

        // ═══════════════════════════════════════════════════════
        // Missile & Explosion System
        // ═══════════════════════════════════════════════════════

        function updateMissiles() {
            for (let i = missiles.length - 1; i >= 0; i--) {
                const missile = missiles[i];

                // Move missile
                const dx = missile.targetX - missile.x;
                const dy = missile.targetY - missile.y;
                const remainingDist = Math.sqrt(dx * dx + dy * dy);

                // Check Obstacles (v2.1) - En route collision
                let hitObstacle = false;
                for (const obs of obstacles) {
                    const dist = Math.sqrt((missile.x - obs.x) ** 2 + (missile.y - obs.y) ** 2);
                    if (dist < obs.size * 0.6) {
                        createExplosion(missile.x, missile.y, missile.ownerId);
                        scene.remove(missile.mesh);
                        missiles.splice(i, 1);
                        hitObstacle = true;
                        break;
                    }
                }
                if (hitObstacle) continue; // Skip rest of loop for this missile

                // Reached Target?
                if (remainingDist < MISSILE_SPEED || missile.traveledDistance >= missile.totalDistance) {
                    // Explode!
                    createExplosion(missile.x, missile.y, missile.ownerId);

                    // Check for hits
                    for (const robot of robots) {
                        const hitDist = Math.sqrt(
                            (robot.x - missile.x) ** 2 + (robot.y - missile.y) ** 2
                        );
                        if (hitDist < SPLASH_RADIUS) {
                            const damage = MISSILE_DAMAGE * (1 - hitDist / SPLASH_RADIUS);
                            robot.damage += damage;
                            if (robot.id !== missile.ownerId) {
                                battleStats.shotsHit[missile.ownerId]++;
                                battleStats.damageDealt[missile.ownerId] += damage;
                                playDamageSound();
                            }
                        }
                    }

                    // Remove missile
                    scene.remove(missile.mesh);
                    missiles.splice(i, 1);
                } else {
                    // Continue moving
                    const moveX = (dx / remainingDist) * MISSILE_SPEED;
                    const moveY = (dy / remainingDist) * MISSILE_SPEED;
                    missile.x += moveX;
                    missile.y += moveY;
                    missile.traveledDistance += MISSILE_SPEED;

                    // Update mesh position
                    const scale = 0.1;
                    missile.mesh.position.x = (missile.x - ARENA_SIZE / 2) * scale;
                    missile.mesh.position.z = (missile.y - ARENA_SIZE / 2) * scale;
                    missile.mesh.position.y = 1;
                }
            }
        }

        function createExplosion(x, y, ownerId) {
            const scale = 0.1;
            const worldX = (x - ARENA_SIZE / 2) * scale;
            const worldZ = (y - ARENA_SIZE / 2) * scale;

            // Explosion ring
            const ringGeometry = new THREE.RingGeometry(0.1, 0.5, 16);
            const ringMaterial = new THREE.MeshBasicMaterial({
                color: 0xff6600,
                transparent: true,
                opacity: 1,
                side: THREE.DoubleSide
            });
            const ring = new THREE.Mesh(ringGeometry, ringMaterial);
            ring.rotation.x = -Math.PI / 2;
            ring.position.set(worldX, 0.5, worldZ);
            scene.add(ring);

            // Play explosion sound
            playExplosionSound();

            explosions.push({
                mesh: ring,
                scale: 0.5,
                maxScale: SPLASH_RADIUS * scale * 0.1,
                opacity: 1
            });
        }

        function updateExplosions() {
            for (let i = explosions.length - 1; i >= 0; i--) {
                const exp = explosions[i];
                exp.scale += 0.3;
                exp.opacity -= 0.05;

                exp.mesh.scale.set(exp.scale, exp.scale, 1);
                exp.mesh.material.opacity = exp.opacity;

                if (exp.opacity <= 0) {
                    scene.remove(exp.mesh);
                    explosions.splice(i, 1);
                }
            }
        }

        function updateMines() {
            const now = Date.now();

            for (let i = mines.length - 1; i >= 0; i--) {
                const mine = mines[i];

                // Arm the mine after delay
                if (!mine.armed && now >= mine.armTime) {
                    mine.armed = true;
                    // Make it pulse when armed
                    mine.mesh.material.emissiveIntensity = 0.6;
                }

                if (!mine.armed) continue;

                // Check for enemy robots (NOT the owner - intelligent mines!)
                for (const robot of robots) {
                    if (robot.id === mine.ownerId) continue; // Skip owner

                    const dx = robot.x - mine.x;
                    const dy = robot.y - mine.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < MINE_TRIGGER_RADIUS) {
                        // BOOM!
                        createExplosion(mine.x, mine.y, mine.ownerId);
                        playExplosionSound();

                        // Damage the enemy robot
                        robot.damage += MINE_DAMAGE;
                        battleStats.damageDealt[mine.ownerId] += MINE_DAMAGE;
                        playDamageSound();

                        // Remove mine
                        scene.remove(mine.mesh);
                        mines.splice(i, 1);
                        debugLog('Mine triggered! Robot ' + robot.id + ' hit for ' + MINE_DAMAGE + ' damage');
                        break;
                    }
                }
            }
        }

        function updateDebris() {
            for (let i = debris.length - 1; i >= 0; i--) {
                const d = debris[i];

                // Apply velocity
                d.x += d.vx;
                d.y += d.vy;
                d.vz -= 0.02; // Gravity
                d.z += d.vz;

                // Update mesh position
                const scale = 0.1;
                d.mesh.position.x = (d.x - ARENA_SIZE / 2) * scale;
                d.mesh.position.z = (d.y - ARENA_SIZE / 2) * scale;
                d.mesh.position.y = d.z;

                // Spin
                d.mesh.rotation.x += d.spin;
                d.mesh.rotation.z += d.spin * 0.7;

                // Remove when hits ground
                if (d.z <= 0) {
                    scene.remove(d.mesh);
                    debris.splice(i, 1);
                }
            }
        }

        function createDeathExplosion(robot) {
            const scale = 0.1;
            const worldX = robot.x;
            const worldY = robot.y;

            // Create 15-20 debris pieces
            const numDebris = 15 + Math.floor(Math.random() * 6);

            for (let i = 0; i < numDebris; i++) {
                const size = 0.1 + Math.random() * 0.2;
                const geometry = new THREE.BoxGeometry(size, size, size);
                const material = new THREE.MeshStandardMaterial({
                    color: robot.color,
                    metalness: 0.5,
                    roughness: 0.5
                });
                const mesh = new THREE.Mesh(geometry, material);

                // Random velocity
                const angle = Math.random() * Math.PI * 2;
                const speed = 2 + Math.random() * 4;

                debris.push({
                    x: worldX,
                    y: worldY,
                    z: 1 + Math.random() * 2,
                    vx: Math.cos(angle) * speed,
                    vy: Math.sin(angle) * speed,
                    vz: 0.3 + Math.random() * 0.5,
                    spin: (Math.random() - 0.5) * 0.3,
                    mesh: mesh
                });

                mesh.position.x = (worldX - ARENA_SIZE / 2) * scale;
                mesh.position.z = (worldY - ARENA_SIZE / 2) * scale;
                mesh.position.y = 1;
                scene.add(mesh);
            }

            // Big explosion at death location
            createExplosion(worldX, worldY, -1);
            createExplosion(worldX + 20, worldY + 20, -1);
            createExplosion(worldX - 20, worldY - 20, -1);
        }

        // ═══════════════════════════════════════════════════════
        // UI Components
        // ═══════════════════════════════════════════════════════

        function createUI() {
            // HTML UI overlay for interactive elements
            const ui = document.createElement('div');
            ui.id = 'game-ui';
            ui.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;font-family:monospace;color:#e2e8f0;';
            appletContainer.appendChild(ui);

            // Recording indicator
            const recordingIndicator = document.createElement('div');
            recordingIndicator.id = 'recording-indicator';
            recordingIndicator.style.cssText = 'position:absolute;top:80px;left:50%;transform:translateX(-50%);background:rgba(220,38,38,0.9);padding:8px 20px;border-radius:20px;display:none;align-items:center;gap:8px;z-index:100;';
            recordingIndicator.innerHTML = `
                <span style="width:12px;height:12px;background:#fff;border-radius:50%;animation:pulse 1s infinite;"></span>
                <span style="font-size:14px;font-weight:bold;">REC</span>
            `;
            ui.appendChild(recordingIndicator);

            // Edit Script Buttons (visible on menu screen)
            const editBtnContainer = document.createElement('div');
            editBtnContainer.id = 'edit-buttons';
            editBtnContainer.style.cssText = 'position:absolute;bottom:35%;left:50%;transform:translateX(-50%);display:flex;gap:20px;pointer-events:auto;';

            const editBlueBtn = document.createElement('button');
            editBlueBtn.textContent = 'Edit Blue Script';
            editBlueBtn.style.cssText = 'background:#3b82f6;border:none;padding:10px 20px;color:white;border-radius:5px;cursor:pointer;font-family:monospace;font-size:14px;';
            editBlueBtn.onclick = () => showScriptEditor(1);

            const editRedBtn = document.createElement('button');
            editRedBtn.textContent = 'Edit Red Script';
            editRedBtn.style.cssText = 'background:#ef4444;border:none;padding:10px 20px;color:white;border-radius:5px;cursor:pointer;font-family:monospace;font-size:14px;';
            editRedBtn.onclick = () => showScriptEditor(2);

            editBtnContainer.appendChild(editBlueBtn);
            editBtnContainer.appendChild(editRedBtn);
            ui.appendChild(editBtnContainer);

            // Add pulse animation
            const style = document.createElement('style');
            style.textContent = '@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }';
            document.head.appendChild(style);
        }

        function updateRobotStatus(robotId, robot) {
            const statusEl = document.getElementById(`robot${robotId + 1}-status`);
            if (!statusEl) return;

            const healthPercent = Math.max(0, 100 - robot.damage);
            const healthColor = healthPercent > 60 ? '#22c55e' : healthPercent > 30 ? '#f59e0b' : '#ef4444';

            const energyPercent = Math.max(0, (robot.energy / MAX_ENERGY) * 100);
            const energyColor = energyPercent > 50 ? '#3b82f6' : energyPercent > 20 ? '#f59e0b' : '#ef4444';

            statusEl.innerHTML = `
            <h3 style = "margin:0 0 10px;color:${robotId === 0 ? '#60a5fa' : '#f87171'};" > Robot ${robotId + 1}</h3>
        <div style="margin-bottom:6px;">
          <span style="color:#9ca3af;font-size:10px;">Health:</span>
          <div style="background:#374151;height:10px;border-radius:3px;margin-top:2px;overflow:hidden;">
            <div style="width:${healthPercent}%;height:100%;background:${healthColor};transition:width 0.2s;"></div>
          </div>
          <span style="font-size:10px;color:${healthColor};">${healthPercent.toFixed(0)}%</span>
        </div>
        <div style="margin-bottom:6px;">
          <span style="color:#9ca3af;font-size:10px;">Energy:</span>
          <div style="background:#374151;height:10px;border-radius:3px;margin-top:2px;overflow:hidden;">
            <div style="width:${energyPercent}%;height:100%;background:${energyColor};transition:width 0.2s;"></div>
          </div>
          <span style="font-size:10px;color:${energyColor};">${energyPercent.toFixed(0)}%</span>
        </div>
        <div style="font-size:10px;color:#9ca3af;">
          <div>Pos: (${Math.floor(robot.x)}, ${Math.floor(robot.y)})</div>
          <div>Speed: ${Math.floor(robot.speed)} | Hdg: ${Math.floor(robot.heading)}deg</div>
        </div>
        `;
        }

        function updateControlPanel() {
            const panel = document.getElementById('control-panel');
            if (!panel) return;

            if (currentState === GameState.MENU) {
                panel.innerHTML = `
            <div style = "margin-bottom:15px;" >
            <button id="edit-robot1" style="background:#3b82f6;border:none;padding:8px 16px;font-size:12px;color:white;border-radius:5px;cursor:pointer;margin-right:10px;">[Edit Robot 1]</button>
            <button id="edit-robot2" style="background:#ef4444;border:none;padding:8px 16px;font-size:12px;color:white;border-radius:5px;cursor:pointer;">[Edit Robot 2]</button>
          </div>
          <button id="start-btn" style="background:#22c55e;border:none;padding:15px 40px;font-size:18px;color:white;border-radius:5px;cursor:pointer;font-family:inherit;font-weight:bold;">
            START BATTLE
          </button>
          <p style="margin:10px 0 0;font-size:12px;color:#6b7280;">Robot 1 (Blue) vs Robot 2 (Red)</p>
        `;
                document.getElementById('start-btn').onclick = startGame;
                document.getElementById('edit-robot1').onclick = function () { showScriptEditor(1); };
                document.getElementById('edit-robot2').onclick = function () { showScriptEditor(2); };
            } else if (currentState === GameState.PLAYING) {
                panel.innerHTML = `
            <div style = "display:flex;gap:30px;" >
            <div style="text-align:left;">
              <div style="color:#60a5fa;font-weight:bold;">Blue (Hunter)</div>
              <div style="font-size:11px;">Shots: ${battleStats.shotsFired[0]} | Hits: ${battleStats.shotsHit[0]}</div>
              <div style="font-size:11px;">Damage: ${battleStats.damageDealt[0].toFixed(1)}</div>
            </div>
            <div style="text-align:left;">
              <div style="color:#f87171;font-weight:bold;">Red (Sniper)</div>
              <div style="font-size:11px;">Shots: ${battleStats.shotsFired[1]} | Hits: ${battleStats.shotsHit[1]}</div>
              <div style="font-size:11px;">Damage: ${battleStats.damageDealt[1].toFixed(1)}</div>
            </div>
          </div>
            `;
            } else if (currentState === GameState.GAME_OVER) {
                // Determine winner
                let winner = -1;

                // 1. Check destruction
                if (robots[0].damage >= 100) winner = 1;
                else if (robots[1].damage >= 100) winner = 0;

                // 2. Check energy limits (most health wins)
                else if (robots[0].energy <= 0 && robots[1].energy <= 0) {
                    if (robots[0].damage < robots[1].damage) winner = 0;
                    else if (robots[1].damage < robots[0].damage) winner = 1;
                }

                // If winner is still -1, it's a draw (handled by battleStats.isDraw)

                const winnerName = winner === 0 ? 'Blue' : 'Red';
                const winnerColor = winner === 0 ? '#60a5fa' : '#f87171';

                const headerHtml = battleStats.isDraw ?
                    `<h2 style = "margin:0 0 15px;color:#fbbf24;" > [DRAW] BATTERIES DEPLETED!</h2> ` :
                    `<h2 style = "margin:0 0 15px;color:${winnerColor};" > [VICTORY] ${winnerName} WINS!</h2> `;

                panel.innerHTML = `
          ${headerHtml}
          
          <div style="background:rgba(255,255,255,0.1);padding:10px;border-radius:5px;margin-bottom:15px;display:flex;justify-content:space-around;font-weight:bold;">
             <span style="color:#60a5fa;">Blue Wins: ${sessionStats.blueWins}</span>
             <span style="color:#fbbf24;font-size:0.9em;opacity:0.8;">(Draws: ${sessionStats.draws})</span>
             <span style="color:#f87171;">Red Wins: ${sessionStats.redWins}</span>
          </div>

          <div style="display:flex;gap:40px;margin-bottom:15px;">
            <div style="text-align:left;">
              <div style="color:#60a5fa;font-weight:bold;">Blue Stats</div>
              <div style="font-size:11px;">Accuracy: ${battleStats.shotsFired[0] > 0 ? ((battleStats.shotsHit[0] / battleStats.shotsFired[0]) * 100).toFixed(1) : 0}%</div>
              <div style="font-size:11px;">Damage: ${battleStats.damageDealt[0].toFixed(1)}</div>
            </div>
            <div style="text-align:left;">
              <div style="color:#f87171;font-weight:bold;">Red Stats</div>
              <div style="font-size:11px;">Accuracy: ${battleStats.shotsFired[1] > 0 ? ((battleStats.shotsHit[1] / battleStats.shotsFired[1]) * 100).toFixed(1) : 0}%</div>
              <div style="font-size:11px;">Damage: ${battleStats.damageDealt[1].toFixed(1)}</div>
            </div>
          </div>
          <div style="display:flex;gap:15px;justify-content:center;">
            <button id="restart-btn" style="background:#22c55e;border:none;padding:12px 30px;font-size:16px;color:white;border-radius:5px;cursor:pointer;font-family:inherit;font-weight:bold;">
              [REMATCH]
            </button>
            <button id="download-btn" style="background:#1d9bf0;border:none;padding:12px 30px;font-size:16px;color:white;border-radius:5px;cursor:pointer;font-family:inherit;font-weight:bold;">
              [Download for X]
            </button>
          </div>
        `;
                document.getElementById('restart-btn').onclick = startGame;
                document.getElementById('download-btn').onclick = downloadRecording;
            }
        }

        // ═══════════════════════════════════════════════════════
        // Game Loop
        // ═══════════════════════════════════════════════════════

        function startGame() {
            debugLog('Starting new game...');

            // Hide 3D overlays and HTML edit buttons
            if (winOverlay) winOverlay.visible = false;
            if (menuOverlay) menuOverlay.visible = false;
            const editBtns = document.getElementById('edit-buttons');
            if (editBtns) editBtns.style.display = 'none';

            // Reset state
            currentState = GameState.PLAYING;
            battleStats = {
                shotsFired: [0, 0],
                shotsHit: [0, 0],
                damageDealt: [0, 0],
                distanceTraveled: [0, 0],
                minesDropped: [0, 0]
            };

            // Clear existing entities
            for (const robot of robots) {
                robot.destroy();
            }
            for (const missile of missiles) {
                scene.remove(missile.mesh);
            }
            for (const exp of explosions) {
                scene.remove(exp.mesh);
            }
            for (const mine of mines) {
                scene.remove(mine.mesh);
            }
            for (const d of debris) {
                scene.remove(d.mesh);
            }
            robots = [];
            missiles = [];
            explosions = [];
            mines = [];
            debris = [];

            // Random spawn positions (corners and edges)
            const spawnPoints = [
                { x: 150, y: 150 },   // Top-left
                { x: 850, y: 150 },   // Top-right
                { x: 150, y: 850 },   // Bottom-left
                { x: 850, y: 850 },   // Bottom-right
                { x: 500, y: 100 },   // Top-center
                { x: 500, y: 900 },   // Bottom-center
                { x: 100, y: 500 },   // Left-center
                { x: 900, y: 500 }    // Right-center
            ];

            // Pick two random different spawn points
            const spawn1Idx = Math.floor(Math.random() * spawnPoints.length);
            let spawn2Idx = Math.floor(Math.random() * spawnPoints.length);
            while (spawn2Idx === spawn1Idx) {
                spawn2Idx = Math.floor(Math.random() * spawnPoints.length);
            }

            const spawn1 = spawnPoints[spawn1Idx];
            const spawn2 = spawnPoints[spawn2Idx];

            // Create robots at random positions
            robots.push(new Robot(0, spawn1.x, spawn1.y, ROBOT_COLORS[0], activeScripts.robot1));
            robots.push(new Robot(1, spawn2.x, spawn2.y, ROBOT_COLORS[1], activeScripts.robot2));

            updateControlPanel();

            // Initialize audio and start engine sounds
            initAudio();
            startEngineSound(0);
            startEngineSound(1);

            // Start video recording automatically
            startRecording();

            // Start game loop
            if (gameLoop) clearInterval(gameLoop);
            gameLoop = setInterval(tick, TICK_INTERVAL);

            debugLog('Game started!');
        }

        function tick() {
            if (currentState !== GameState.PLAYING) return;

            // Execute AI for each robot
            for (const robot of robots) {
                robot.executeAI();
            }

            // Update physics
            for (const robot of robots) {
                robot.update();
                robot.updateUI(); // Fix: Update 3D health bars (v2.4)
                updateRobotStatus(robot.id, robot);
            }

            updateMissiles();
            updateExplosions();
            updateMines();
            updateDebris();
            update3DHealthBars(); // Update 3D HUD for recording (v2.4.7)

            // Check victory condition
            let gameOver = false;
            let draw = false;

            // 1. Destruction Check (Instant Win) - damage >= 100
            for (const robot of robots) {
                if (robot.damage >= 100) {
                    gameOver = true;
                    break;
                }
            }

            // 2. Dominant Victory - robot has MORE energy AND MORE health AND opponent out of energy
            if (!gameOver) {
                for (let i = 0; i < 2; i++) {
                    const other = 1 - i;
                    const hasMoreEnergy = robots[i].energy > robots[other].energy;
                    const hasMoreHealth = robots[i].damage < robots[other].damage;
                    const opponentOutOfEnergy = robots[other].energy <= 0;

                    if (hasMoreEnergy && hasMoreHealth && opponentOutOfEnergy) {
                        gameOver = true;
                        break;
                    }
                }
            }

            // 3. Both out of energy - compare health (robot with more health wins)
            if (!gameOver && robots[0].energy <= 0 && robots[1].energy <= 0) {
                gameOver = true;
                if (Math.abs(robots[0].damage - robots[1].damage) < 0.1) {
                    draw = true;
                }
            }

            if (gameOver) {
                endGame(draw);
                return;
            }

            // Update stats display
            updateControlPanel();

            // Render
            renderer.render(scene, camera);
        }

        function endGame(isDraw = false) {
            currentState = GameState.GAME_OVER;
            // Store draw state globally so UI can access it
            battleStats.isDraw = isDraw;

            if (gameLoop) {
                clearInterval(gameLoop);
                gameLoop = null;
            }

            // Determine winner
            // Win conditions:
            // 1. Opponent destroyed (damage >= 100)
            // 2. Both out of energy - more health wins
            let winner = -1; // -1 = draw/undetermined
            if (!isDraw) {
                if (robots[0].damage >= 100) {
                    winner = 1; // Red wins (Blue destroyed)
                    sessionStats.redWins++;
                } else if (robots[1].damage >= 100) {
                    winner = 0; // Blue wins (Red destroyed)
                    sessionStats.blueWins++;
                } else if (robots[0].damage < robots[1].damage) {
                    winner = 0; // Blue has more health (both out of energy)
                    sessionStats.blueWins++;
                } else {
                    winner = 1; // Red has more health or equal
                    sessionStats.redWins++;
                }
            } else {
                sessionStats.draws++;
            }

            // Create death explosion only for destroyed robots
            for (const robot of robots) {
                if (robot.damage >= 100) {
                    createDeathExplosion(robot);
                    robot.destroy();
                }
            }

            // Stop engine sounds
            stopAllEngineSounds();

            if (!isDraw) {
                playVictorySound();
            }

            // Update 3D Win Screen (v2.4)
            if (winOverlay) {
                updateWinOverlay(isDraw, winner === 0 ? 'Blue' : 'Red');
                winOverlay.visible = true;
            }

            // Render the win screen first so it gets captured in the recording
            renderer.render(scene, camera);

            // Keep rendering the win screen for 2 seconds before stopping recording
            // This ensures the end screen is captured in the video
            let endScreenFrames = 0;
            const endScreenInterval = setInterval(() => {
                renderer.render(scene, camera);
                endScreenFrames++;
                if (endScreenFrames >= 120) { // ~2 seconds at 60fps
                    clearInterval(endScreenInterval);
                    stopRecording();
                    debugLog('Game over! ' + (isDraw ? 'DRAW' : 'Winner decided'));
                }
            }, 1000 / 60);
        }

        // ═══════════════════════════════════════════════════════
        // HUD System (v2.4) - Full 3D UI for Recording
        // ═══════════════════════════════════════════════════════

        let winOverlay = null;
        let winMesh = null;
        let hudBars = [null, null]; // 3D health bar meshes for recording
        let menuOverlay = null; // 3D menu for start screen
        let menuMesh = null;
        let hudClickables = []; // Clickable 3D UI elements
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();

        // Click handler for 3D UI
        function onCanvasClick(event) {
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(hudClickables);

            if (intersects.length > 0) {
                const clicked = intersects[0].object;
                if (clicked.userData.action === 'start') {
                    startGame();
                } else if (clicked.userData.action === 'edit1') {
                    showScriptEditor(1);
                } else if (clicked.userData.action === 'edit2') {
                    showScriptEditor(2);
                } else if (clicked.userData.action === 'rematch') {
                    startGame();
                } else if (clicked.userData.action === 'download') {
                    downloadRecording();
                }
            }
        }

        function createHUD() {
            // Title Bar
            const titleCanvas = document.createElement('canvas');
            titleCanvas.width = 512;
            titleCanvas.height = 64;
            const ctx = titleCanvas.getContext('2d');

            // Background
            ctx.fillStyle = 'rgba(15, 23, 42, 0.8)'; // Dark Blue
            ctx.fillRect(0, 0, 512, 64);

            // Text
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 32px monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('AI ROBOT WARS v2.4', 256, 32);

            const titleTex = new THREE.CanvasTexture(titleCanvas);
            const titleMat = new THREE.MeshBasicMaterial({
                map: titleTex,
                transparent: true
            });
            const titlePlane = new THREE.PlaneGeometry(60, 7.5); // Aspect ratio match
            const titleMesh = new THREE.Mesh(titlePlane, titleMat);

            // Attach to camera (HUD)
            // Ortho camera: (0,0) is center. Top is +viewSize (60).
            // Position near top
            titleMesh.position.set(0, 52, -10);
            camera.add(titleMesh);

            // 3D Health Bars (for recording capture)
            for (let i = 0; i < 2; i++) {
                const barCanvas = document.createElement('canvas');
                barCanvas.width = 200;
                barCanvas.height = 120;

                const barTex = new THREE.CanvasTexture(barCanvas);
                const barMat = new THREE.MeshBasicMaterial({
                    map: barTex,
                    transparent: true
                });
                const barPlane = new THREE.PlaneGeometry(25, 15);
                const barMesh = new THREE.Mesh(barPlane, barMat);

                // Position: left side for robot 0, right side for robot 1
                const xPos = i === 0 ? -85 : 85;
                barMesh.position.set(xPos, 35, -10);
                camera.add(barMesh);

                hudBars[i] = {
                    canvas: barCanvas,
                    ctx: barCanvas.getContext('2d'),
                    texture: barTex,
                    mesh: barMesh
                };
            }

            // Win Overlay (Hidden initially) - Larger for full stats
            const winCanvas = document.createElement('canvas');
            winCanvas.width = 512;
            winCanvas.height = 256; // Larger for stats
            winMesh = { canvas: winCanvas, ctx: winCanvas.getContext('2d'), texture: null };

            // Initial render (will be overwritten)
            winMesh.texture = new THREE.CanvasTexture(winCanvas);
            const winMat = new THREE.MeshBasicMaterial({
                map: winMesh.texture,
                transparent: true
            });

            const winPlane = new THREE.PlaneGeometry(80, 40); // Taller for stats
            winOverlay = new THREE.Mesh(winPlane, winMat);
            winOverlay.position.set(0, 0, -10); // Center
            winOverlay.visible = false;
            winOverlay.userData.action = 'rematch'; // Make clickable for rematch
            hudClickables.push(winOverlay);
            camera.add(winOverlay);

            // 3D Menu Overlay (Start Screen)
            const menuCanvas = document.createElement('canvas');
            menuCanvas.width = 512;
            menuCanvas.height = 300;
            menuMesh = { canvas: menuCanvas, ctx: menuCanvas.getContext('2d'), texture: null };

            menuMesh.texture = new THREE.CanvasTexture(menuCanvas);
            const menuMat = new THREE.MeshBasicMaterial({
                map: menuMesh.texture,
                transparent: true
            });

            const menuPlane = new THREE.PlaneGeometry(70, 42);
            menuOverlay = new THREE.Mesh(menuPlane, menuMat);
            menuOverlay.position.set(0, -10, -10);
            menuOverlay.visible = true; // Starts visible
            menuOverlay.userData.action = 'start';
            hudClickables.push(menuOverlay);
            camera.add(menuOverlay);

            // Initial render of menu
            updateMenuOverlay();

            scene.add(camera); // Ensure camera is in scene for children to render

            // Add click listener to canvas
            renderer.domElement.addEventListener('click', onCanvasClick);
        }

        function updateMenuOverlay() {
            if (!menuMesh) return;
            const ctx = menuMesh.ctx;
            const w = 512, h = 300;

            ctx.clearRect(0, 0, w, h);

            // Background
            ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
            ctx.fillRect(0, 0, w, h);

            // Border
            ctx.strokeStyle = '#60a5fa';
            ctx.lineWidth = 4;
            ctx.strokeRect(4, 4, w - 8, h - 8);

            // Title
            ctx.fillStyle = '#60a5fa';
            ctx.font = 'bold 28px monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText('AI ROBOT WARS', w / 2, 20);

            ctx.fillStyle = '#9ca3af';
            ctx.font = '14px monospace';
            ctx.fillText(APPLET_VERSION, w / 2, 55);

            // Start Button
            ctx.fillStyle = '#22c55e';
            ctx.fillRect(w / 2 - 100, 90, 200, 50);
            ctx.strokeStyle = '#16a34a';
            ctx.lineWidth = 2;
            ctx.strokeRect(w / 2 - 100, 90, 200, 50);

            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 20px monospace';
            ctx.fillText('START BATTLE', w / 2, 120);

            // Instructions (edit buttons are HTML overlay)
            ctx.fillStyle = '#6b7280';
            ctx.font = '12px monospace';
            ctx.fillText('Blue vs Red • Last robot standing wins!', w / 2, 170);
            ctx.fillText('Use buttons below to edit robot scripts', w / 2, 190);

            menuMesh.texture.needsUpdate = true;
        }

        function update3DHealthBars() {
            if (!hudBars[0] || !robots.length) return;

            for (let i = 0; i < 2; i++) {
                const bar = hudBars[i];
                const robot = robots[i];
                if (!bar || !robot) continue;

                const ctx = bar.ctx;
                ctx.clearRect(0, 0, 200, 120);

                // Background
                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                ctx.fillRect(0, 0, 200, 120);

                // Border
                ctx.strokeStyle = i === 0 ? '#60a5fa' : '#f87171';
                ctx.lineWidth = 3;
                ctx.strokeRect(2, 2, 196, 116);

                // Title
                ctx.fillStyle = i === 0 ? '#60a5fa' : '#f87171';
                ctx.font = 'bold 16px monospace';
                ctx.textAlign = 'center';
                ctx.fillText(i === 0 ? 'BLUE' : 'RED', 100, 20);

                // Health Bar
                const healthPercent = Math.max(0, 100 - robot.damage) / 100;
                const healthColor = healthPercent > 0.6 ? '#22c55e' : healthPercent > 0.3 ? '#f59e0b' : '#ef4444';

                ctx.fillStyle = '#374151';
                ctx.fillRect(15, 35, 170, 15);
                ctx.fillStyle = healthColor;
                ctx.fillRect(15, 35, 170 * healthPercent, 15);

                ctx.fillStyle = '#ffffff';
                ctx.font = '12px monospace';
                ctx.textAlign = 'left';
                ctx.fillText('HP: ' + Math.floor(healthPercent * 100) + '%', 15, 65);

                // Energy Bar
                const energyPercent = Math.max(0, robot.energy / MAX_ENERGY);
                const energyColor = energyPercent > 0.5 ? '#3b82f6' : energyPercent > 0.2 ? '#f59e0b' : '#ef4444';

                ctx.fillStyle = '#374151';
                ctx.fillRect(15, 75, 170, 15);
                ctx.fillStyle = energyColor;
                ctx.fillRect(15, 75, 170 * energyPercent, 15);

                ctx.fillStyle = '#ffffff';
                ctx.fillText('EN: ' + Math.floor(energyPercent * 100) + '%', 15, 105);

                bar.texture.needsUpdate = true;
            }
        }

        function updateWinOverlay(isDraw, winnerName) {
            const ctx = winMesh.ctx;
            const w = 512, h = 256; // Larger canvas for stats

            // Resize canvas if needed
            if (winMesh.canvas.height !== h) {
                winMesh.canvas.width = w;
                winMesh.canvas.height = h;
            }

            ctx.clearRect(0, 0, w, h);

            // Background
            ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
            ctx.fillRect(0, 0, w, h);

            // Border with winner color
            ctx.strokeStyle = isDraw ? '#fbbf24' : (winnerName === 'Blue' ? '#60a5fa' : '#f87171');
            ctx.lineWidth = 4;
            ctx.strokeRect(4, 4, w - 8, h - 8);

            // Victory Header
            ctx.fillStyle = isDraw ? '#fbbf24' : (winnerName === 'Blue' ? '#60a5fa' : '#f87171');
            ctx.font = 'bold 32px monospace';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            const headerText = isDraw ? "DRAW!" : `${winnerName.toUpperCase()} WINS!`;
            ctx.fillText(headerText, w / 2, 15);

            // Session Stats Bar
            ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.fillRect(20, 55, w - 40, 25);

            ctx.font = 'bold 14px monospace';
            ctx.fillStyle = '#60a5fa';
            ctx.textAlign = 'left';
            ctx.fillText(`Blue: ${sessionStats.blueWins}`, 30, 72);

            ctx.fillStyle = '#fbbf24';
            ctx.textAlign = 'center';
            ctx.fillText(`Draws: ${sessionStats.draws}`, w / 2, 72);

            ctx.fillStyle = '#f87171';
            ctx.textAlign = 'right';
            ctx.fillText(`Red: ${sessionStats.redWins}`, w - 30, 72);

            // Battle Stats - Blue
            ctx.font = '12px monospace';
            ctx.textAlign = 'left';

            ctx.fillStyle = '#60a5fa';
            ctx.font = 'bold 14px monospace';
            ctx.fillText('BLUE', 30, 100);

            ctx.font = '12px monospace';
            ctx.fillStyle = '#ffffff';
            const blueAcc = battleStats.shotsFired[0] > 0 ? ((battleStats.shotsHit[0] / battleStats.shotsFired[0]) * 100).toFixed(0) : 0;
            ctx.fillText(`Accuracy: ${blueAcc}%`, 30, 120);
            ctx.fillText(`Damage: ${battleStats.damageDealt[0].toFixed(1)}`, 30, 140);
            ctx.fillText(`Shots: ${battleStats.shotsFired[0]}`, 30, 160);

            // Battle Stats - Red
            ctx.textAlign = 'right';

            ctx.fillStyle = '#f87171';
            ctx.font = 'bold 14px monospace';
            ctx.fillText('RED', w - 30, 100);

            ctx.font = '12px monospace';
            ctx.fillStyle = '#ffffff';
            const redAcc = battleStats.shotsFired[1] > 0 ? ((battleStats.shotsHit[1] / battleStats.shotsFired[1]) * 100).toFixed(0) : 0;
            ctx.fillText(`Accuracy: ${redAcc}%`, w - 30, 120);
            ctx.fillText(`Damage: ${battleStats.damageDealt[1].toFixed(1)}`, w - 30, 140);
            ctx.fillText(`Shots: ${battleStats.shotsFired[1]}`, w - 30, 160);

            // Footer
            ctx.fillStyle = '#9ca3af';
            ctx.font = '11px monospace';
            ctx.textAlign = 'center';
            ctx.fillText('AI ROBOT WARS - Download for X.com!', w / 2, h - 20);

            winMesh.texture.needsUpdate = true;
        }

        // ═══════════════════════════════════════════════════════
        // Window Resize Handler
        // ═══════════════════════════════════════════════════════

        function onWindowResize() {
            const aspect = window.innerWidth / window.innerHeight;
            const viewSize = 60;
            camera.left = -viewSize * aspect;
            camera.right = viewSize * aspect;
            camera.top = viewSize;
            camera.bottom = -viewSize;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        window.addEventListener('resize', onWindowResize);

        // ═══════════════════════════════════════════════════════
        // Initialize
        // ═══════════════════════════════════════════════════════

        debugLog('Initializing game...');
        initScene();
        createUI(); // Initialize HTML UI overlay (health bars, control panel)


        // Initial render
        renderer.render(scene, camera);

        debugLog('✅ AI Robot Wars ready!');
        console.log('═══════════════════════════════════════════════════');
        console.log('🤖 Ready to battle! Click START BATTLE to begin.');
        console.log('═══════════════════════════════════════════════════');

    } catch (err) {
        console.error('AI Robot Wars Error:', err);
        const container = document.getElementById('applet-root');
        if (container) {
            container.innerHTML = `
            <div style = "padding:30px;color:#ff4444;font-family:monospace;background:#1a2e40;min-height:100vh;" >
            <h1>Error Loading AI Robot Wars</h1>
            <pre style="background:#0a1929;padding:20px;border-radius:5px;overflow:auto;">${err.message}\n\n${err.stack}</pre>
          </div>
            `;
        }
    }
})();
