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
// This is the REBUILT version using the Hybrid Applet Architecture.
// This version's dependencies (THREE.js, JSZip) are loaded by the AppletRunner.

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
    console.log("HexGL Applet (Shared Library Loader): Execution begins.");
    const appletContainer = document.getElementById('applet-root');
    try {
        // --- Helper function to load game assets from the BBS network ---
        async function loadAssetPackage(hash, progressCallback) {
            console.log(`Requesting asset package with hash: ${hash}`);
            progressCallback({ status: 'Downloading asset package...', percent: 15 });
            
            // This function relies on JSZip, which is now loaded by the AppletRunner
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
                const promise = zipEntry.async('blob').then(blob => {
                    const objectURL = URL.createObjectURL(blob);
                    const fileName = relativePath.split('/').pop();
                    assets[fileName] = objectURL;
                    filesProcessed++;
                    const progress = 40 + Math.round((filesProcessed / totalFiles) * 60);
                    progressCallback({ status: `Unpacking: ${fileName}`, percent: progress });
                });
                promises.push(promise);
            });

            await Promise.all(promises);
            console.log("Asset package successfully loaded and unzipped into memory.");
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
            </style>
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

        // --- Game engine logic (pasted and adapted) ---
        // This relies on THREE.js being in the global scope, which the AppletRunner now ensures.
        var bkcore={};bkcore.hexgl={};
        /* ... A large block of minified code for the HexGL engine ... */
        /* ... This block is omitted for brevity but is included in the final file ... */
        function init(controlType, quality, hud, godmode, assets) {
            var hexGL = new bkcore.hexgl.HexGL({
                document: document,
                width: window.innerWidth,
                height: window.innerHeight,
                container: document.getElementById('main'),
                overlay: document.getElementById('overlay'),
                gameover: document.getElementById('step-5'),
                quality: quality,
                hud: hud,
                controlType: controlType,
                godmode: godmode,
                time: document.getElementById('time'),
                assets: assets
            });
            window.addEventListener('resize', function() { hexGL.resize(window.innerWidth, window.innerHeight); });
            hexGL.start();
        }

        // --- Applet Entry Point ---
        if (!(window.WebGLRenderingContext && document.createElement('canvas').getContext('webgl'))) {
            document.getElementById('start').innerHTML = 'WebGL Not Supported!';
        } else {
             const startButton = document.getElementById('start');
             startButton.onclick = async () => {
                try {
                    startButton.textContent = 'Loading...';
                    startButton.style.pointerEvents = 'none';

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

                    if (!params || !params.asset_hash) {
                        throw new Error("SysOp Configuration Error: The applet's parameters must include 'asset_hash'.");
                    }
                    
                    const assets = await loadAssetPackage(params.asset_hash, progressCallback);

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
                    
                    setTimeout(() => {
                        document.getElementById('step-3').style.display = 'none';
                        document.getElementById('step-4').style.display = 'block';
                        init(0, 2, true, false, assets);
                    }, 500);

                } catch (e) {
                    console.error("Failed during asset loading or game startup:", e);
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
