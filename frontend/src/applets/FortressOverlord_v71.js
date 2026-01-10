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


// Full path: axon_bbs/frontend/src/applets/FortressOverlord.js
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
  saveData: function(newData) { return this._postMessage('saveData', newData); },
  getAppletInfo: function() { return this._postMessage('getAppletInfo'); },
  postEvent: function(eventData) { return this._postMessage('postEvent', eventData); },
  readEvents: function() { return this._postMessage('readEvents'); }
};
window.addEventListener('message', (event) => window.bbs._handleMessage(event));
// --- End of Applet API Helper ---


// --- Main Applet Execution ---
(async function() {
    // --- 1. SETUP: Styles, HTML, and Game Configuration ---
    const APPLET_VERSION = "v7.1"; 

    const styles = `
        :root {
            --gunmetal-dark: #121518; --gunmetal-medium: #1d2125; --gunmetal-light: #2a2f34;
            --border-color: #0c0e10; --text-primary: #e2e8f0; --accent-green: #32cd32;
            --accent-red: #d94a4a; --shadow-color: rgba(0,0,0,0.5);
        }
        html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; }
        body { font-family: 'Lucida Console', 'Courier New', monospace; background-color: var(--gunmetal-dark); color: var(--text-primary); display: flex; align-items: center; justify-content: center; }
        
        #site-selection-screen { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--gunmetal-dark); }
        #globe-container { width: 68vmin; height: 68vmin; max-width: 600px; max-height: 600px; cursor: pointer; }
        .selection-header { text-align: center; margin-bottom: 20px; }
        .selection-header h1 { font-size: 2rem; color: var(--accent-green); text-shadow: 0 0 5px var(--accent-green); margin: 0; }
        .selection-header p { color: var(--text-primary); margin-top: 5px; }
        #confirm-landing-button { background-color: var(--accent-green); color: #000; border: 2px solid #55ff55; padding: 10px 20px; font-size: 1.2rem; font-family: inherit; cursor: pointer; margin-top: 20px; box-shadow: 0 0 10px var(--accent-green); transition: all 0.2s; }
        #confirm-landing-button:disabled { background-color: var(--gunmetal-medium); color: #666; border-color: var(--border-color); box-shadow: none; cursor: not-allowed; }

        #console-screen { display: none; width: 100%; height: 100%; }
        .console-container {
            width: 100%; height: 100%; max-width: 1920px; max-height: 1080px;
            background: linear-gradient(145deg, var(--gunmetal-light), var(--gunmetal-medium));
            padding: 20px; box-sizing: border-box; display: grid; grid-template-columns: 320px 1fr 320px;
            grid-template-rows: auto 1fr; gap: 15px; border: 3px solid var(--border-color);
            border-radius: 15px; box-shadow: inset 0 0 15px var(--shadow-color), 0 0 20px var(--shadow-color);
            position: relative;
        }
        .panel { background: linear-gradient(var(--gunmetal-medium), var(--gunmetal-dark)); border: 2px solid var(--border-color); border-radius: 6px; padding: 15px; display: flex; flex-direction: column; box-shadow: inset 0 0 10px var(--shadow-color); }
        .center-panel { padding: 15px; display: flex; flex-direction: column; }
        .header { grid-column: 1 / -1; text-align: center; padding-bottom: 10px; border-bottom: 3px solid var(--border-color); }
        .header h1 { margin: 0; font-size: 1.8rem; color: var(--accent-green); text-shadow: 0 0 5px var(--accent-green); }
        .version-tag { position: absolute; top: 25px; right: 25px; font-size: 0.8rem; color: #666; }
        .emergency-light { position: absolute; top: -12px; left: 50%; transform: translateX(-50%); width: 40px; height: 20px; background: radial-gradient(circle at 50% 100%, #ff4b4b, #a71d1d); border-radius: 15px 15px 0 0; border: 2px solid #000; box-shadow: 0 -2px 10px var(--accent-red), inset 0 -2px 5px rgba(0,0,0,0.6); z-index: 10; }
        .emergency-light::after { content: ''; position: absolute; top: 3px; left: 10px; width: 20px; height: 4px; background: rgba(255, 255, 255, 0.6); border-radius: 50%; filter: blur(2px); transform: rotate(-10deg); }
        h2, h3 { font-size: 1.2rem; color: var(--accent-green); border-bottom: 1px solid var(--border-color); padding-bottom: 8px; margin-top: 0; text-transform: uppercase; letter-spacing: 1px; }
        h3 { font-size: 1rem; margin-bottom: 10px; }
        .gauge-container { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .telemetry-screen, .main-panel-content, .command-log { background-color: #080c08; border: 2px solid #223a22; border-radius: 4px; color: var(--accent-green); position: relative; overflow: hidden; }
        .telemetry-screen::after, .main-panel-content::after, .command-log::after { content: ' '; display: block; position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: linear-gradient(to bottom, rgba(30, 60, 30, 0.15) 50%, rgba(10, 20, 10, 0.2) 50%); background-size: 100% 4px; pointer-events: none; z-index: 2; }
        .telemetry-screen { flex-grow: 1; display: flex; flex-direction: column; }
        .main-panel-content { flex-grow: 1; padding: 0; box-sizing: border-box; display: flex; flex-direction: column; }
        #map-canvas.crosshair-cursor { cursor: crosshair; }
        .view-toggles { display: flex; gap: 5px; margin-bottom: 10px; }
        .view-toggles button { background-color: var(--gunmetal-medium); border: 2px solid var(--border-color); color: var(--text-primary); padding: 5px 10px; cursor: pointer; font-family: inherit; font-size: 0.8rem; box-shadow: inset 0 2px 5px rgba(0,0,0,0.4); }
        .view-toggles button.active { background-color: var(--accent-green); color: #000; font-weight: bold; border-color: #55ff55; }
        .resource-display, .command-log { font-size: 0.9rem; }
        .resource-display div { display: flex; justify-content: space-between; padding: 2px 0; }
        .command-log { height: 200px; overflow-y: auto; margin-top: 10px; padding: 5px; font-size: 0.8rem; }
        .log-entry { margin-bottom: 4px; }
        .log-entry.info { color: var(--accent-green); }
        .log-entry.warn { color: #facc15; }
        .log-entry.error { color: var(--accent-red); }
        #video-playback-screen { height: 120px; background-color: #000; margin-bottom: 10px; border: 2px solid #223a22; border-radius: 4px; }
        #sensor-feed-display { flex-grow: 1; background-color: #080c08; border: 2px solid #223a22; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 0.9rem; padding: 10px; box-sizing: border-box; }
        #debug-dialog { display: none; position: absolute; bottom: 10px; right: 10px; width: 350px; height: 250px; background-color: rgba(0,0,0,0.8); border: 1px solid var(--accent-green); border-radius: 5px; color: #fc8181; font-family: inherit; font-size: 12px; overflow-y: scroll; padding-top: 25px; z-index: 1000; }
        #debug-header { position: absolute; top: 0; left: 0; right: 0; background-color: var(--accent-green); color: #000; font-weight: bold; padding: 3px; cursor: move; user-select: none; }
        #reset-button { background-color: var(--accent-red); color: #fff; border: 1px solid #ff7b7b; padding: 8px; font-family: inherit; cursor: pointer; margin-top: auto; }
        .management-list { list-style: none; padding: 0; margin: 0; overflow-y: auto; flex-grow: 1; }
        .management-item { background-color: var(--gunmetal-medium); padding: 10px; border-radius: 4px; margin-bottom: 8px; border: 1px solid var(--border-color); }
        .management-item-header { display: flex; justify-content: space-between; align-items: center; }
        .management-item-title { font-weight: bold; color: var(--text-primary); }
        .management-item-body { font-size: 0.8rem; color: #a0aec0; margin-top: 8px; }
        .management-item-actions button, .construct-button { font-size: 0.7rem; padding: 4px 8px; background-color: var(--gunmetal-light); border: 1px solid var(--border-color); color: var(--text-primary); cursor: pointer; margin-left: 5px; border-radius: 3px; }
        .management-item-actions button:hover, .construct-button:hover { background-color: var(--accent-green); color: #000; }
        .construct-section { margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border-color); }
        .construct-section div { display: flex; justify-content: space-around; }
    `;
    document.head.appendChild(Object.assign(document.createElement("style"), { innerText: styles }));

    document.getElementById('applet-root').innerHTML = `
        <div id="site-selection-screen">
            <div class="selection-header">
                <h1>Establish Fortress Location</h1>
                <p>Rotate globe and select a landing zone.</p>
            </div>
            <div id="globe-container"></div>
            <button id="confirm-landing-button" disabled>CONFIRM LANDING SITE</button>
        </div>
        <div id="console-screen">
            <div class="console-container">
                <div class="emergency-light"></div>
                <div class="header">
                    <h1>FORTRESS OVERLORD</h1>
                    <div class="version-tag">Version ${APPLET_VERSION}</div>
                </div>
                <div class="panel left-panel">
                    <h2>SYSTEM STATUS</h2>
                    <div class="gauge-container" id="gauge-display"></div>
                    <h2>DRONE TELEMETRY</h2>
                    <div class="telemetry-screen" id="telemetry-display">
                        <div id="video-playback-screen"></div>
                        <div id="sensor-feed-display"><p>NO SIGNAL</p></div>
                    </div>
                    <button id="reset-button">RESET GAME STATE</button>
                </div>
                <div class="panel center-panel">
                    <div class="view-toggles" id="view-toggles">
                        <button class="active" data-view="map">STRAT-MAP</button>
                        <button data-view="buildings">BUILDINGS</button>
                        <button data-view="units">UNITS</button>
                    </div>
                    <div class="main-panel-content" id="main-view"></div>
                </div>
                <div class="panel right-panel">
                    <h2>RESOURCES</h2>
                    <div class="resource-display" id="resource-display"></div>
                    <h2>COMMAND LOG</h2>
                    <div class="command-log" id="event-log"></div>
                </div>
                <div id="debug-dialog"><div id="debug-header">DEBUG CONSOLE</div></div>
            </div>
        </div>
    `;

    let userInfo = null, gameState = null;
    const confirmButton = document.getElementById('confirm-landing-button');

    function setupDebugConsole() { if (window.BBS_DEBUG_MODE === true) { /* ... */ } }
    function debugLog(message) { if (window.BBS_DEBUG_MODE !== true) return; console.log(message); }
    
    function logEvent(message, level = 'info') {
        const eventLogEl = document.getElementById('event-log');
        if (!eventLogEl) return;
        const entry = document.createElement('div');
        entry.classList.add('log-entry', level);
        entry.textContent = `> ${message}`;
        eventLogEl.appendChild(entry);
        eventLogEl.scrollTop = eventLogEl.scrollHeight;
    }

    function getInitialGameState() { 
        return { 
            resources: { rawOre: 0, crystals: 200, alloy: 100 }, 
            power: { current: 50, max: 100 }, 
            temperature: 25.5, 
            pressure: 101.3, 
            oxygen: 98.2, 
            landingSite: null,
            drones: [
                { id: 'drone_01', type: 'Scout', status: 'Idle', x: 60, y: -30, health: 100, inventory: { rawOre: 0 } }
            ],
            buildings: [
                { id: 'cc_01', type: 'Command Center', x: 0, y: 0, health: 1000 }
            ],
            mapFeatures: [
                { id: 'ore_01', type: 'Ore Deposit', x: -80, y: 50 },
                { id: 'gas_01', type: 'Hydrogen Geyser', x: 100, y: 120 }
            ]
        }; 
    }

    function initSiteSelection() {
        const globeContainer = document.getElementById('globe-container');
        let scene, camera, renderer, globe, marker, raycaster, mouse;
        let isDragging = false, previousMousePosition = { x: 0, y: 0 };

        function init() {
            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(75, globeContainer.clientWidth / globeContainer.clientHeight, 0.1, 1000);
            camera.position.z = 1.5;
            renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(globeContainer.clientWidth, globeContainer.clientHeight);
            globeContainer.appendChild(renderer.domElement);

            const texture = new THREE.CanvasTexture(createVenusTexture());
            const material = new THREE.MeshBasicMaterial({ map: texture });
            const geometry = new THREE.SphereGeometry(1, 32, 32);
            globe = new THREE.Mesh(geometry, material);
            scene.add(globe);

            raycaster = new THREE.Raycaster();
            mouse = new THREE.Vector2();
            
            renderer.domElement.addEventListener('mousedown', onMouseDown);
            renderer.domElement.addEventListener('mousemove', onMouseMove);
            renderer.domElement.addEventListener('mouseup', onMouseUp);
            renderer.domElement.addEventListener('click', onClick);
            window.addEventListener('resize', onWindowResize, false);
            
            animate();
        }

        function createVenusTexture() {
            const canvas = document.createElement('canvas');
            canvas.width = 512; canvas.height = 256;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#D2691E';
            ctx.fillRect(0, 0, 512, 256);
            for(let i=0; i<30; i++) {
                ctx.fillStyle = `rgba(165, 42, 42, ${Math.random()*0.4+0.2})`;
                ctx.beginPath(); ctx.arc(Math.random()*512, Math.random()*256, Math.random()*50+10, 0, Math.PI*2); ctx.fill();
            }
            ctx.strokeStyle = "rgba(0,0,0,0.2)";
            for(let i=0; i<512; i+=32) { ctx.beginPath(); ctx.moveTo(i,0); ctx.lineTo(i,256); ctx.stroke(); }
            for(let i=0; i<256; i+=32) { ctx.beginPath(); ctx.moveTo(0,i); ctx.lineTo(512,i); ctx.stroke(); }
            return canvas;
        }

        function onMouseDown(event) { isDragging = true; previousMousePosition.x = event.clientX; previousMousePosition.y = event.clientY; }
        function onMouseMove(event) { if (isDragging) { const dX = event.clientX-previousMousePosition.x, dY = event.clientY-previousMousePosition.y; globe.rotation.y += dX*0.005; globe.rotation.x += dY*0.005; previousMousePosition.x=event.clientX; previousMousePosition.y=event.clientY; } }
        function onMouseUp() { isDragging = false; }
        
        function onClick(event) {
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObject(globe);
            if (intersects.length > 0) {
                const point = intersects[0].point;
                if (!marker) {
                    const markerGeo = new THREE.SphereGeometry(0.03, 16, 16);
                    const markerMat = new THREE.MeshBasicMaterial({ color: 0x32cd32 });
                    marker = new THREE.Mesh(markerGeo, markerMat); scene.add(marker);
                }
                marker.position.copy(point);
                confirmButton.disabled = false;
                gameState.landingSite = { x: point.x, y: point.y, z: point.z };
            }
        }
        function onWindowResize() { 
            if(renderer && camera && globeContainer){
                camera.aspect = globeContainer.clientWidth / globeContainer.clientHeight; 
                camera.updateProjectionMatrix(); 
                renderer.setSize(globeContainer.clientWidth, globeContainer.clientHeight); 
            }
        }
        function animate() { requestAnimationFrame(animate); renderer.render(scene, camera); }
        
        if (typeof THREE === 'undefined') {
            const script = document.createElement('script');
            script.src = "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js";
            script.onload = init; document.head.appendChild(script);
        } else { init(); }
    }

    function initCommandConsole() {
        const consoleScreen = document.getElementById('console-screen');
        const siteSelectionScreen = document.getElementById('site-selection-screen');
        siteSelectionScreen.style.display = 'none';
        consoleScreen.style.display = 'block';

        const gaugeDisplay = document.getElementById('gauge-display');
        const resourceDisplayEl = document.getElementById('resource-display');
        const mainViewEl = document.getElementById('main-view');
        const resetButton = document.getElementById('reset-button');
        const videoScreenEl = document.getElementById('video-playback-screen');
        const sensorFeedEl = document.getElementById('sensor-feed-display');
        let processedEventIds = new Set();
        let commandState = { active: false, command: null, sourceId: null, payload: {} };
        
        mainViewEl.innerHTML = `
            <div id="view-map" style="width:100%; height:100%; display:block; background-color: #080c08;">
                <canvas id="map-canvas" style="width: 100%; height: 100%;"></canvas>
            </div>
            <div id="view-buildings" style="width:100%; height:100%; display:none; flex-direction: column;"></div>
            <div id="view-units" style="width:100%; height:100%; display:none; flex-direction: column;"></div>
        `;
        const viewMap = mainViewEl.querySelector('#view-map');
        const viewBuildings = mainViewEl.querySelector('#view-buildings');
        const viewUnits = mainViewEl.querySelector('#view-units');
        const mapCanvas = document.getElementById('map-canvas');

        async function submitCommand(subject, body) {
            try {
                await bbs.postEvent({ subject, body: JSON.stringify(body) });
                logEvent(`CMD SUBMIT: ${subject} ${JSON.stringify(body)}`, 'info');
            } catch (e) {
                logEvent(`CMD FAILED: ${e.message}`, 'error');
                debugLog(`Failed to post event: ${e.message}`);
            }
        }

        async function pollForEvents() {
            try {
                const events = await bbs.readEvents();
                const newEvents = events.filter(e => !processedEventIds.has(e.id));

                if (newEvents.length > 0) {
                    newEvents.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                    
                    for (const event of newEvents) {
                        processedEventIds.add(event.id);
                        if (event.author_display === 'overlord_agent') {
                            try {
                                const eventBody = JSON.parse(event.body);
                                logEvent(`AGENT: ${eventBody.summary}`, 'info');
                            } catch (e) {
                                logEvent(`AGENT RAW: ${event.body}`, 'warn');
                            }
                        }
                    }
                }
            } catch (e) {
                debugLog(`Failed to poll for events: ${e.message}`);
            }
        }


        function simulateVideoFeed() {
            const canvas = document.createElement('canvas');
            videoScreenEl.appendChild(canvas);
            const ctx = canvas.getContext('2d');
            function resize() { canvas.width = videoScreenEl.clientWidth; canvas.height = videoScreenEl.clientHeight; }
            window.addEventListener('resize', resize);
            resize();
            let noise = new ImageData(canvas.width, canvas.height);
            function draw() {
                for (let i = 0; i < noise.data.length; i += 4) {
                    const val = Math.random() * 50;
                    noise.data[i] = val; noise.data[i + 1] = val + 20; noise.data[i + 2] = val; noise.data[i + 3] = 255;
                }
                ctx.putImageData(noise, 0, 0);
                requestAnimationFrame(draw);
            }
            draw();
        }

        function drawGauge(id, label, value, max) {
            let canvas = document.getElementById(id);
            if (!canvas) {
                const gaugeWrapper = document.createElement('div');
                gaugeWrapper.className = 'gauge';
                gaugeWrapper.innerHTML = `<canvas id="${id}" width="120" height="80"></canvas><div style="text-align:center; font-size: 0.8em; color: var(--text-primary);">${label}</div>`;
                gaugeDisplay.appendChild(gaugeWrapper);
                canvas = document.getElementById(id);
            }
            const ctx = canvas.getContext('2d');
            const percent = Math.min(Math.max(value / max, 0), 1);
            ctx.clearRect(0,0,120,80); ctx.strokeStyle='#000'; ctx.lineWidth=10; ctx.beginPath(); ctx.arc(60,60,40,Math.PI,2*Math.PI); ctx.stroke();
            ctx.strokeStyle='#2a2f34'; ctx.lineWidth=8; ctx.beginPath(); ctx.arc(60,60,40,Math.PI,2*Math.PI); ctx.stroke();
            ctx.strokeStyle=`hsl(${(1-percent)*120}, 80%, 50%)`; ctx.beginPath(); ctx.arc(60,60,40,Math.PI,Math.PI+(percent*Math.PI)); ctx.stroke();
            ctx.fillStyle='var(--text-primary)'; ctx.font='16px "Lucida Console", monospace'; ctx.textAlign='center'; ctx.fillText(Math.round(value), 60, 60);
        }
        function renderGauges() { if (!gameState) return; const p=gameState.power||{c:0,m:100}; drawGauge('temp-gauge','TEMP',gameState.temperature||25,50); drawGauge('pressure-gauge','PRESSURE',gameState.pressure||101,120); drawGauge('oxygen-gauge','OXY',gameState.oxygen||98,100); drawGauge('power-gauge','POWER',p.current,p.max); }
        function renderResources() { if (!gameState) return; const r=gameState.resources||{c:0,a:0}; resourceDisplayEl.innerHTML=`<div><span>RAW ORE:</span><span style="color:var(--accent-green);">${Math.floor(r.rawOre || 0)}</span></div><div><span>CRYSTALS:</span><span style="color:var(--accent-green);">${Math.floor(r.crystals)}</span></div><div><span>ALLOY:</span><span style="color:var(--accent-green);">${Math.floor(r.alloy)}</span></div>`;}
        
        function renderMainView(view) {
            document.querySelectorAll('#view-toggles button').forEach(b => b.classList.remove('active'));
            document.querySelector(`#view-toggles button[data-view="${view}"]`).classList.add('active');
            
            viewMap.style.display = 'none';
            viewBuildings.style.display = 'none';
            viewUnits.style.display = 'none';

            if (view === 'map') {
                viewMap.style.display = 'block';
                drawStrategicMap();
            } else if (view === 'buildings') {
                viewBuildings.style.display = 'flex';
                renderBuildingView();
            } else if (view === 'units') {
                viewUnits.style.display = 'flex';
                renderUnitView();
            }
        }
        
        function displayTelemetry(obj) {
            if (!obj) {
                sensorFeedEl.innerHTML = '<p>NO SIGNAL</p>';
                return;
            }
            let html = `<div style="text-align: left; width: 100%; font-size: 0.8rem;">`;
            html += `<div><strong>ID:</strong> ${obj.id}</div>`;
            html += `<div><strong>TYPE:</strong> ${obj.type}</div>`;
            if (obj.status) html += `<div><strong>STATUS:</strong> ${obj.status}</div>`;
            if (obj.health) html += `<div><strong>INTEGRITY:</strong> ${obj.health}%</div>`;
            if (obj.inventory) html += `<div><strong>CARGO:</strong> ${obj.inventory.rawOre || 0} Raw Ore</div>`;
            html += `</div>`;
            sensorFeedEl.innerHTML = html;
        }

        function renderBuildingView() {
            let html = `<h3>BUILDING MANAGEMENT</h3>`;
            html += `<ul class="management-list">`;
            (gameState.buildings || []).forEach(b => {
                html += `
                    <li class="management-item" data-id="${b.id}">
                        <div class="management-item-header">
                            <span class="management-item-title">${b.type} (${b.id})</span>
                            <div class="management-item-actions">
                                <button data-action="upgrade">UPGRADE</button>
                                <button data-action="repair">REPAIR</button>
                            </div>
                        </div>
                        <div class="management-item-body">
                            <span>INTEGRITY: ${b.health}/1000</span>
                        </div>
                    </li>
                `;
            });
            html += `</ul>`;
            viewBuildings.innerHTML = html;
        }

        function renderUnitView() {
            let html = `<h3>DRONE ROSTER</h3>`;
            html += `<ul class="management-list">`;
            (gameState.drones || []).forEach(d => {
                html += `
                    <li class="management-item" data-id="${d.id}">
                        <div class="management-item-header">
                            <span class="management-item-title">${d.type} (${d.id})</span>
                            <div class="management-item-actions">
                                <button data-action="build">BUILD</button>
                                <button data-action="harvest-ore">HARVEST ORE</button>
                            </div>
                        </div>
                        <div class="management-item-body">
                            <span>STATUS: ${d.status}</span> | <span>INTEGRITY: ${d.health}%</span>
                        </div>
                    </li>
                `;
            });
            html += `</ul>`;
            viewUnits.innerHTML = html;
        }

        function drawStrategicMap() {
            const canvas = document.getElementById('map-canvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.clientWidth;
            canvas.height = canvas.clientHeight;
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;

            ctx.fillStyle = '#080c08';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = 'rgba(50, 205, 50, 0.3)';
            ctx.lineWidth = 1;
            for(let i=0; i < canvas.width; i+=20) { ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, canvas.height); ctx.stroke(); }
            for(let i=0; i < canvas.height; i+=20) { ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(canvas.width, i); ctx.stroke(); }

            const allObjects = [...(gameState.buildings || []), ...(gameState.drones || []), ...(gameState.mapFeatures || [])];
            allObjects.forEach(obj => {
                const drawX = centerX + obj.x;
                const drawY = centerY + obj.y;

                ctx.strokeStyle = '#fff';
                ctx.fillStyle = 'var(--accent-green)';
                ctx.lineWidth = 1;

                if(obj.type.includes('Construction Site')){
                    ctx.globalAlpha = 0.5;
                    ctx.strokeRect(drawX - 5, drawY - 5, 10, 10);
                    ctx.globalAlpha = 1.0;
                } else {
                    switch(obj.type) {
                        case 'Command Center':
                            ctx.fillRect(drawX - 5, drawY - 5, 10, 10);
                            ctx.strokeRect(drawX - 5, drawY - 5, 10, 10);
                            break;
                        case 'Scout':
                            ctx.beginPath();
                            ctx.moveTo(drawX, drawY - 6);
                            ctx.lineTo(drawX - 5, drawY + 4);
                            ctx.lineTo(drawX + 5, drawY + 4);
                            ctx.closePath();
                            ctx.stroke();
                            break;
                        case 'Ore Deposit':
                            ctx.fillStyle = '#b0a090';
                            ctx.beginPath();
                            ctx.moveTo(drawX, drawY - 6); ctx.lineTo(drawX + 6, drawY);
                            ctx.lineTo(drawX + 3, drawY + 6); ctx.lineTo(drawX - 3, drawY + 6);
                            ctx.lineTo(drawX - 6, drawY); ctx.closePath();
                            ctx.fill();
                            break;
                        case 'Hydrogen Geyser':
                             ctx.strokeStyle = '#add8e6';
                             ctx.beginPath(); ctx.arc(drawX, drawY, 6, 0, Math.PI*2); ctx.stroke();
                             for(let i=0; i<3; i++){ ctx.beginPath(); ctx.moveTo(drawX - 4 + i*4, drawY - 6); ctx.quadraticCurveTo(drawX - 6 + i*4, drawY-12, drawX-4+i*4, drawY-18); ctx.stroke();}
                             break;
                    }
                }
            });

            ctx.fillStyle = 'rgba(50, 205, 50, 0.7)';
            ctx.font = '14px "Lucida Console", monospace';
            ctx.textAlign = 'left';
            ctx.fillText('SECTOR 7G // AO: FORTRESS', 10, 20);
        }
        
        viewBuildings.addEventListener('click', (e) => {
            // Placeholder for future direct building management
        });

        viewUnits.addEventListener('click', (e) => {
            if (e.target.tagName !== 'BUTTON') return;
            const action = e.target.dataset.action;
            const itemElement = e.target.closest('.management-item');
            const droneId = itemElement.dataset.id;
            
            if (action === 'harvest-ore') {
                commandState = { active: true, command: 'HARVEST', sourceId: droneId, payload: {} };
                mapCanvas.classList.add('crosshair-cursor');
                logEvent(`Awaiting target for HARVEST command from ${droneId}...`, 'warn');
                renderMainView('map');
            } else if (action === 'build') {
                commandState = { active: true, command: 'BUILD', sourceId: droneId, payload: { buildingType: 'Greenhouse' } }; // Default to greenhouse
                mapCanvas.classList.add('crosshair-cursor');
                logEvent(`Awaiting placement location for GREENHOUSE from ${droneId}...`, 'warn');
                renderMainView('map');
            }
        });

        mapCanvas.addEventListener('click', (e) => {
            const canvas = e.target;
            const rect = canvas.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            
            const worldX = Math.round(clickX - centerX);
            const worldY = Math.round(clickY - centerY);

            const allObjects = [...(gameState.drones || []), ...(gameState.buildings || []), ...(gameState.mapFeatures || [])];
            let clickedObject = null;
            
            for(const obj of allObjects) {
                const objScreenX = centerX + obj.x;
                const objScreenY = centerY + obj.y;
                const distance = Math.sqrt(Math.pow(clickX - objScreenX, 2) + Math.pow(clickY - objScreenY, 2));
                if (distance < 10) {
                    clickedObject = obj;
                    break;
                }
            }

            if (commandState.active) {
                if (commandState.command === 'HARVEST') {
                    if (clickedObject && (clickedObject.type === 'Ore Deposit' || clickedObject.type === 'Hydrogen Geyser')) {
                        submitCommand('ASSIGN_TASK', { 
                            droneId: commandState.sourceId, 
                            task: 'HARVEST', 
                            targetId: clickedObject.id 
                        });
                    } else {
                        logEvent('Invalid target for HARVEST command.', 'error');
                    }
                } else if (commandState.command === 'BUILD') {
                    submitCommand('BUILD', { 
                        droneId: commandState.sourceId, 
                        buildingType: commandState.payload.buildingType, 
                        coords: { x: worldX, y: worldY }
                    });
                }
                commandState = { active: false, command: null, sourceId: null, payload: {} };
                mapCanvas.classList.remove('crosshair-cursor');
            } else {
                displayTelemetry(clickedObject);
            }
        });

        renderGauges();
        renderResources();
        renderMainView('map');
        
        logEvent("Connecting to Overlord Agent...");
        setTimeout(() => logEvent("Telemetry link established."), 1000);
        setTimeout(() => logEvent(`Welcome, Commander ${userInfo.nickname || userInfo.username}.`), 1500);
        setTimeout(() => logEvent("All systems nominal. Awaiting input."), 2500);
        simulateVideoFeed();
        
        resetButton.addEventListener('click', async () => {
            try {
                await bbs.saveData(getInitialGameState());
                debugLog("Game state reset. Reloading applet...");
                window.location.reload();
            } catch (e) {
                debugLog(`Error resetting game state: ${e.message}`);
            }
        });
        
        document.getElementById('view-toggles').addEventListener('click', e => { if (e.target.tagName === 'BUTTON') renderMainView(e.target.dataset.view); });
        window.addEventListener('resize', () => { 
            renderGauges(); 
            if (document.querySelector('#view-toggles button[data-view="map"].active')) {
                drawStrategicMap();
            }
        });
        debugLog("Command Console Initialized.");
        setInterval(pollForEvents, 10000);
    }
    
    try {
        setupDebugConsole();
        debugLog(`Fortress Overlord ${APPLET_VERSION} Initializing...`);
        userInfo = await bbs.getUserInfo();
        let loadedData = await bbs.getData();

        gameState = getInitialGameState();
        if (loadedData) {
            debugLog("Found saved data. Merging and validating...");
            gameState = { ...gameState, ...loadedData };
            
            ['buildings', 'drones', 'mapFeatures'].forEach(key => {
                if(loadedData[key] && !Array.isArray(loadedData[key])) {
                    gameState[key] = getInitialGameState()[key];
                    logEvent(`Save data mismatch: Resetting '${key}'.`, 'warn');
                }
            });
        }

        if (gameState.landingSite) {
            debugLog("Landing site found. Loading command console.");
            initCommandConsole();
        } else {
            debugLog("No landing site found. Initializing globe...");
            initSiteSelection();
        }

        confirmButton.addEventListener('click', async () => {
            if (gameState.landingSite) {
                try {
                    await bbs.saveData(gameState);
                    debugLog(`Landing site confirmed and saved: ${JSON.stringify(gameState.landingSite)}`);
                    initCommandConsole();
                } catch(e) {
                    debugLog(`Error saving landing site: ${e.message}`);
                }
            }
        });
    } catch (e) {
        document.getElementById('applet-root').innerHTML = `<p style="color:red;">CRITICAL ERROR: ${e.message}</p>`;
        console.error("Applet initialization failed:", e);
    }
})();


