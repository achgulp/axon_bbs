// Fortress Overlord v11.0 - Complete Game Edition
// Copyright (C) 2025 Achduke7 - Licensed under GPL v3

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
        if (command === 'getUserInfo') resolve({ username: 'test', nickname: 'Test', pubkey: 'abc123' });
        else if (command === 'getAppletInfo') resolve({ id: 'test', name: 'Fortress Overlord', parameters: {} });
        else resolve({});
      }
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

(async function() {
try {
    const APPLET_VERSION = "v19.0 - GameBoard Stability";

    function debugLog(msg) {
        if (!window.BBS_DEBUG_MODE) return;
        const ts = new Date().toISOString().split('T')[1].slice(0,-1);
        const log = '[FO ' + ts + '] ' + msg;
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

        // Show version prominently at top
        const versionDiv = document.createElement('div');
        versionDiv.textContent = '=== FORTRESS OVERLORD ' + APPLET_VERSION + ' ===';
        versionDiv.style.cssText = 'font-size:0.8rem;color:#ffff00;font-weight:bold;margin-bottom:5px;border-bottom:1px solid #32cd32;padding-bottom:3px;';
        dp.appendChild(versionDiv);
    }

    debugLog("CHECKPOINT 1: Initializing Fortress Overlord " + APPLET_VERSION);

    function loadLib(src) {
        return new Promise((resolve, reject) => {
            const s = document.createElement('script');
            s.src = src;
            s.crossOrigin = 'anonymous';
            s.onload = () => { debugLog('Loaded: ' + src.split('/').pop()); resolve(); };
            s.onerror = () => reject(new Error('Failed: ' + src));
            document.head.appendChild(s);
        });
    }

    debugLog("CHECKPOINT 2: Loading libraries");
    await loadLib('https://unpkg.com/react@18.2.0/umd/react.production.min.js');
    await loadLib('https://unpkg.com/react-dom@18.2.0/umd/react-dom.production.min.js');
    await loadLib('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js');
    await loadLib('https://unpkg.com/tone@14.8.49/build/Tone.js');

    debugLog("CHECKPOINT 3: Libraries loaded");
    debugLog("React exists: " + (!!window.React));
    debugLog("ReactDOM exists: " + (!!window.ReactDOM));
    debugLog("THREE exists: " + (!!window.THREE));
    debugLog("Tone exists: " + (!!window.Tone));

    if (!window.React) throw new Error('React failed to load');
    if (!window.ReactDOM) throw new Error('ReactDOM failed to load');
    if (!window.THREE) throw new Error('THREE.js failed to load');
    if (!window.Tone) throw new Error('Tone.js failed to load');

    const { React, ReactDOM } = window;
    const { useState, useEffect, useCallback, useMemo, useRef } = React;

    // Constants
    const GameState = { Lobby: 'LOBBY', Game: 'GAME' };
    const UnitType = { Tank: 'TANK', Drone: 'DRONE' };
    const GameEventType = {
        JoinGame: 'JOIN_GAME',
        StartGame: 'START_GAME',
        BuildUnit: 'BUILD_UNIT',
        MoveUnit: 'MOVE_UNIT',
        UnitAttack: 'UNIT_ATTACK',
        GameOver: 'GAME_OVER'
    };

    const AI_USER = { nickname: 'Fortress AI', pubkey: 'ai_opponent', isAI: true };
    const GAME_SUBJECT = 'FORTRESS_OVERLORD_V1';
    const MAP_SIZE = { width: 40, depth: 50 };
    const PLAYER_COLORS = [0x007bff, 0xff4136];
    const FORTRESS_HEALTH = 2000;
    const STARTING_RESOURCES = 500;
    const RESOURCE_GEN_RATE = 2;
    const UNIT_STATS = {
        TANK: { cost: 100, health: 100, speed: 2.5, damage: 10, range: 1.5 },
        DRONE: { cost: 75, health: 50, speed: 4, damage: 5, range: 1 }
    };

    debugLog("CHECKPOINT 4: Constants defined");

    // Game Service
    let procEventIds = new Set();
    const gameSvc = {
        async postEvent(evt, sender) {
            try {
                await window.bbs.postEvent({
                    subject: GAME_SUBJECT,
                    body: JSON.stringify({ ...evt, sender, timestamp: Date.now() })
                });
                debugLog('Posted: ' + evt.type);
            } catch (e) {
                debugLog('Post ERROR: ' + e.message);
            }
        },
        async pollEvents(cb) {
            try {
                const evts = await window.bbs.readEvents();
                const newEvts = evts
                    .filter(e => e.subject === GAME_SUBJECT && !procEventIds.has(e.id))
                    .sort((a,b) => a.id - b.id);
                for (const e of newEvts) {
                    procEventIds.add(e.id);
                    try {
                        cb(JSON.parse(e.body));
                        debugLog('Received: ' + JSON.parse(e.body).type);
                    } catch (err) { debugLog('Parse ERROR: ' + err.message); }
                }
            } catch (e) { debugLog('Poll ERROR: ' + e.message); }
        },
        startPolling(cb, interval = 1000) {
            const poll = () => this.pollEvents(cb);
            poll();
            return setInterval(poll, interval);
        },
        stopPolling(id) {
            if (id) clearInterval(id);
            // DO NOT clear procEventIds - we need to remember processed events!
            debugLog('Stopped polling (keeping event history)');
        }
    };

    debugLog("CHECKPOINT 5: Game service ready");

    // Sound Service
    const sndSvc = {
        synths: {},
        init: false,
        async initialize() {
            if (!window.Tone || this.init) return;
            if (window.Tone.context.state !== 'running') await window.Tone.start();
            this.synths.build = new window.Tone.Synth().toDestination();
            this.synths.explosion = new window.Tone.MetalSynth().toDestination();
            this.synths.explosion.volume.value = -10;
            this.init = true;
            debugLog("Sound initialized");
        },
        async play(sound) {
            if (!this.init) await this.initialize();
            const now = window.Tone.now();
            if (sound === 'build') this.synths.build.triggerAttackRelease('C4', '8n', now);
            if (sound === 'explosion') this.synths.explosion.triggerAttackRelease('C2', '4n', now);
        }
    };

    // Styles
    const css = document.createElement('style');
    css.textContent = '*{box-sizing:border-box;margin:0;padding:0}html,body,#applet-root{width:100%;height:100%;overflow:hidden}body{font-family:monospace;background:#1a2e40;color:#e2e8f0}.flex{display:flex}.flex-col{flex-direction:column}.items-center{align-items:center}.justify-center{justify-content:center}.justify-between{justify-content:space-between}.h-screen{height:100vh}.w-full{width:100%}.h-full{height:100%}.text-xl{font-size:1.25rem}.text-4xl{font-size:2.25rem}.text-lg{font-size:1.125rem}.font-bold{font-weight:700}.mb-4{margin-bottom:1rem}.mb-8{margin-bottom:2rem}.mt-4{margin-top:1rem}.p-3{padding:0.75rem}.p-4{padding:1rem}.px-8{padding-left:2rem;padding-right:2rem}.py-4{padding-top:1rem;padding-bottom:1rem}.rounded-lg{border-radius:0.5rem}.bg-blue-600{background:#2563eb}.bg-green-600{background:#16a34a}.bg-gray-700{background:#374151}.bg-gray-800{background:#1f2937}.bg-gray-900{background:#111827}.text-blue-400{color:#60a5fa}.text-gray-300{color:#d1d5db}.text-gray-500{color:#6b7280}.text-white{color:#fff}.text-red-500{color:#ef4444}.shadow-2xl{box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}.absolute{position:absolute}.relative{position:relative}.inset-0{top:0;right:0;bottom:0;left:0}.pointer-events-none{pointer-events:none}.pointer-events-auto{pointer-events:auto}.space-x-4>*+*{margin-left:1rem}.text-sm{font-size:0.875rem}.text-center{text-align:center}.text-right{text-align:right}.bottom-4{bottom:1rem}.transition{transition:all 0.2s}.cursor-not-allowed{cursor:not-allowed}.text-2xl{font-size:1.5rem}button{cursor:pointer;font-family:inherit}button:hover{opacity:0.9}button:disabled{opacity:0.5;cursor:not-allowed}';
    document.head.appendChild(css);
    debugLog("CHECKPOINT 6: Styles applied");

    // React Components
    const HealthBar = ({health, maxHealth, color}) => {
        const pct = (health / maxHealth) * 100;
        return React.createElement('div', {className: 'w-full bg-gray-700 rounded-lg', style: {height: '10px'}},
            React.createElement('div', {className: 'h-full rounded-lg', style: {width: pct+'%', backgroundColor: color, height: '10px'}}));
    };

    const UI = ({player, opponent, worldState, onBuildUnit, selectedUnit}) => {
        const pFort = worldState.fortresses.find(f => f.ownerId === player.id);
        const oFort = worldState.fortresses.find(f => f.ownerId === (1-player.id));
        const pRes = Math.floor(worldState.resources[player.id]);

        return React.createElement('div', {className: 'absolute inset-0 pointer-events-none p-4 flex flex-col justify-between'},
            React.createElement('div', {className: 'flex justify-between items-start text-lg'},
                React.createElement('div', {className: 'p-3 rounded-lg', style: {width:'25%', background:'rgba(0,0,0,0.5)'}},
                    React.createElement('p', {className: 'font-bold', style: {color: '#'+player.color.toString(16)}}, player.nickname + ' (You)'),
                    React.createElement('p', null, 'Resources: ', React.createElement('span', {style: {fontFamily:'monospace'}}, pRes)),
                    pFort && React.createElement(HealthBar, {health: pFort.health, maxHealth: pFort.maxHealth, color: '#'+player.color.toString(16)})
                ),
                React.createElement('div', {className: 'p-3 rounded-lg text-right', style: {width:'25%', background:'rgba(0,0,0,0.5)'}},
                    React.createElement('p', {className: 'font-bold', style: {color: '#'+PLAYER_COLORS[1-player.id].toString(16)}}, opponent.nickname),
                    oFort && React.createElement(HealthBar, {health: oFort.health, maxHealth: oFort.maxHealth, color: '#'+PLAYER_COLORS[1-player.id].toString(16)})
                )
            ),
            React.createElement('div', {className: 'flex justify-center items-end'},
                React.createElement('div', {className: 'p-3 rounded-lg flex items-center space-x-4 pointer-events-auto', style: {background:'rgba(0,0,0,0.5)'}},
                    selectedUnit ? React.createElement('div', {className: 'text-center', style: {width:'256px'}},
                        React.createElement('h3', {className: 'text-lg font-bold'}, selectedUnit.type),
                        React.createElement(HealthBar, {health: selectedUnit.health, maxHealth: selectedUnit.maxHealth, color: '#'+player.color.toString(16)}),
                        React.createElement('p', null, Math.ceil(selectedUnit.health) + ' / ' + selectedUnit.maxHealth + ' HP')
                    ) : Object.keys(UNIT_STATS).map(ut => {
                        const st = UNIT_STATS[ut];
                        const canAfford = pRes >= st.cost;
                        return React.createElement('button', {
                            key: ut,
                            onClick: () => canAfford && onBuildUnit(ut),
                            disabled: !canAfford,
                            className: 'p-4 rounded-lg transition ' + (canAfford ? 'bg-gray-700' : 'bg-gray-800 text-gray-500 cursor-not-allowed')
                        },
                            React.createElement('p', {className: 'font-bold text-lg'}, ut),
                            React.createElement('p', {className: 'text-sm'}, 'Cost: ', React.createElement('span', {style:{fontFamily:'monospace'}}, st.cost))
                        );
                    })
                )
            )
        );
    };

    const GameBoard = ({worldState, setWorldState, player, selectedUnit, onUnitSelect}) => {
        const mountRef = useRef(null);
        const gameRef = useRef(null);
        const selectedUnitRef = useRef(selectedUnit);
        const playerRef = useRef(player);
        const worldStateRef = useRef(worldState);
        const onUnitSelectRef = useRef(onUnitSelect);
        const setWorldStateRef = useRef(setWorldState);

        selectedUnitRef.current = selectedUnit;
        playerRef.current = player;
        worldStateRef.current = worldState;
        onUnitSelectRef.current = onUnitSelect;
        setWorldStateRef.current = setWorldState;

        const handleClick = useCallback((event) => {
            if (!gameRef.current) return;
            const {raycaster, mouse, camera, scene} = gameRef.current;
            mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
            raycaster.setFromCamera(mouse, camera);
            const ints = raycaster.intersectObjects(scene.children, true);

            if (selectedUnitRef.current) {
                const gnd = ints.find(i => i.object.name === 'ground');
                if (gnd) {
                    const tgt = ints.find(i => i.object.userData.type === 'unit' || i.object.userData.type === 'fortress');
                    let tgtId = null;
                    if (tgt && tgt.object.userData.ownerId !== playerRef.current.id) tgtId = tgt.object.userData.id;
                    setWorldStateRef.current(prev => ({...prev, units: prev.units.map(u => u.id === selectedUnitRef.current.id ? {...u, targetId: tgtId} : u)}));
                    gameSvc.postEvent({type: GameEventType.MoveUnit, payload: {unitId: selectedUnitRef.current.id, targetId: tgtId}}, playerRef.current);
                    onUnitSelectRef.current(null);
                    debugLog('Unit moved: ' + selectedUnitRef.current.id);
                    return;
                }
            }

            const uInt = ints.find(i => i.object.userData.type === 'unit');
            if (uInt) {
                const u = worldStateRef.current.units.find(u => u.id === uInt.object.userData.id);
                if (u) { onUnitSelectRef.current(u); debugLog('Unit selected: ' + u.id); return; }
            }
            onUnitSelectRef.current(null);
        }, []);

        useEffect(() => {
            if (!mountRef.current) return;
            debugLog(">>> GameBoard: Initializing Three.js (should only happen ONCE)");

            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a2e40);
            const asp = window.innerWidth / window.innerHeight;
            const d = MAP_SIZE.depth / 2 + 10;
            const cam = new THREE.OrthographicCamera(-d*asp, d*asp, d, -d, 1, 1000);
            cam.position.set(10, 30, 10);
            cam.lookAt(0, 0, 0);

            const rend = new THREE.WebGLRenderer({antialias: true});
            rend.setSize(window.innerWidth, window.innerHeight);
            rend.shadowMap.enabled = true;
            mountRef.current.appendChild(rend.domElement);

            const aLight = new THREE.AmbientLight(0xffffff, 0.5);
            scene.add(aLight);
            const dLight = new THREE.DirectionalLight(0xffffff, 0.8);
            dLight.position.set(10, 20, 5);
            dLight.castShadow = true;
            scene.add(dLight);

            const gndGeo = new THREE.PlaneGeometry(MAP_SIZE.width, MAP_SIZE.depth);
            const gndMat = new THREE.MeshStandardMaterial({color: 0x334155});
            const gnd = new THREE.Mesh(gndGeo, gndMat);
            gnd.rotation.x = -Math.PI / 2;
            gnd.receiveShadow = true;
            gnd.name = 'ground';
            scene.add(gnd);

            gameRef.current = {scene, camera: cam, renderer: rend, raycaster: new THREE.Raycaster(), mouse: new THREE.Vector2(), unitMap: new Map(), fortressMap: new Map()};

            mountRef.current.addEventListener('pointerdown', handleClick);

            const animate = () => {
                if (!gameRef.current) return;
                setWorldStateRef.current(prev => {
                    const ns = {...prev, units: [...prev.units], fortresses: [...prev.fortresses]};
                    const dt = 1/60;
                    ns.units.forEach(u => {
                        if (u.targetId) {
                            const tU = ns.units.find(x => x.id === u.targetId);
                            const tF = ns.fortresses.find(x => x.id === u.targetId);
                            const t = tU || tF;
                            if (t) {
                                const uPos = new THREE.Vector3(u.position.x, u.position.y, u.position.z);
                                const tPos = new THREE.Vector3(t.position.x, t.position.y, t.position.z);
                                const dist = uPos.distanceTo(tPos);
                                const ust = UNIT_STATS[u.type];
                                if (dist > ust.range) {
                                    const dir = tPos.clone().sub(uPos).normalize();
                                    u.position.x += dir.x * ust.speed * dt;
                                    u.position.z += dir.z * ust.speed * dt;
                                } else if (u.ownerId === playerRef.current.id) {
                                    gameSvc.postEvent({type: GameEventType.UnitAttack, payload: {attackerId: u.id, targetId: t.id, damage: ust.damage}}, playerRef.current);
                                }
                            } else u.targetId = null;
                        }
                    });
                    return ns;
                });
                rend.render(scene, cam);
                requestAnimationFrame(animate);
            };
            animate();

            const cm = mountRef.current;
            return () => {
                debugLog(">>> GameBoard: CLEANUP - Three.js destroyed (should not happen during game!)");
                if (cm) { cm.removeChild(rend.domElement); cm.removeEventListener('pointerdown', handleClick); }
            };
        }, [handleClick]);

        useEffect(() => {
            if (!gameRef.current) return;
            const {scene, unitMap, fortressMap} = gameRef.current;

            worldState.fortresses.forEach(f => {
                if (!fortressMap.has(f.id)) {
                    const geo = new THREE.BoxGeometry(6, 4, 6);
                    const mat = new THREE.MeshStandardMaterial({color: PLAYER_COLORS[f.ownerId]});
                    const m = new THREE.Mesh(geo, mat);
                    m.position.set(f.position.x, 2, f.position.z);
                    m.castShadow = true;
                    m.userData = {id: f.id, type: 'fortress', ownerId: f.ownerId};
                    scene.add(m);
                    fortressMap.set(f.id, m);
                }
            });

            const curIds = new Set(worldState.units.map(u => u.id));
            unitMap.forEach((m, id) => { if (!curIds.has(id)) { scene.remove(m); unitMap.delete(id); } });

            worldState.units.forEach(u => {
                let m = unitMap.get(u.id);
                if (!m) {
                    const geo = u.type === 'TANK' ? new THREE.BoxGeometry(1, 0.5, 1.5) : new THREE.SphereGeometry(0.6, 16, 8);
                    const mat = new THREE.MeshStandardMaterial({color: PLAYER_COLORS[u.ownerId]});
                    m = new THREE.Mesh(geo, mat);
                    m.castShadow = true;
                    m.userData = {id: u.id, type: 'unit', ownerId: u.ownerId};
                    scene.add(m);
                    unitMap.set(u.id, m);
                }
                m.position.set(u.position.x, 0.25, u.position.z);
                m.material.emissive.setHex(selectedUnit?.id === u.id ? 0xffff00 : 0x000000);
            });
        }, [worldState, selectedUnit]);

        return React.createElement('div', {ref: mountRef, className: 'w-full h-full'});
    };

    const Game = ({player, opponent, onGameOver}) => {
        debugLog(">>> Game component MOUNTED - Player: " + player.nickname + " vs " + opponent.nickname);

        const initWS = useMemo(() => ({
            fortresses: [
                {id: 'f0', ownerId: 0, position: {x:0, y:0, z: MAP_SIZE.depth/2-2}, health: FORTRESS_HEALTH, maxHealth: FORTRESS_HEALTH},
                {id: 'f1', ownerId: 1, position: {x:0, y:0, z: -MAP_SIZE.depth/2+2}, health: FORTRESS_HEALTH, maxHealth: FORTRESS_HEALTH}
            ],
            units: [],
            resources: [STARTING_RESOURCES, STARTING_RESOURCES]
        }), []);

        const [worldState, setWorldState] = useState(initWS);
        const [selectedUnit, setSelectedUnit] = useState(null);
        const pollId = useRef(null);
        const resId = useRef(null);
        const aiId = useRef(null);

        const handleUnitSel = useCallback((u) => {
            setSelectedUnit(u && u.ownerId === playerRef.current.id ? u : null);
        }, []);

        const handleBuild = useCallback((ut) => {
            const cost = UNIT_STATS[ut].cost;
            if (worldStateRef.current.resources[playerRef.current.id] >= cost) {
                const uid = playerRef.current.id + '-' + ut + '-' + Date.now();
                const z = playerRef.current.id === 0 ? MAP_SIZE.depth/2-5 : -MAP_SIZE.depth/2+5;
                const x = (Math.random()-0.5) * (MAP_SIZE.width-4);
                gameSvc.postEvent({type: GameEventType.BuildUnit, payload: {unitId: uid, unitType: ut, ownerId: playerRef.current.id, position: {x, y:0, z}}}, playerRef.current);
                setWorldState(p => ({...p, resources: p.resources.map((r,i) => i === playerRef.current.id ? r-cost : r)}));
                sndSvc.play('build');
                debugLog('Built: ' + ut);
            }
        }, []);

        const opponentRef = useRef(opponent);
        const worldStateRef = useRef(worldState);
        opponentRef.current = opponent;
        worldStateRef.current = worldState;

        const aiTick = useCallback(() => {
            if (!opponentRef.current.isAI) return;
            const aiId = 1 - playerRef.current.id;
            const aiRes = worldStateRef.current.resources[aiId];
            const canT = aiRes >= UNIT_STATS.TANK.cost;
            const canD = aiRes >= UNIT_STATS.DRONE.cost;
            if (canT || canD) {
                const ut = canT && Math.random() > 0.4 ? 'TANK' : canD ? 'DRONE' : null;
                if (ut) {
                    const uid = aiId + '-' + ut + '-' + Date.now();
                    const z = aiId === 0 ? MAP_SIZE.depth/2-5 : -MAP_SIZE.depth/2+5;
                    const x = (Math.random()-0.5) * (MAP_SIZE.width-4);
                    gameSvc.postEvent({type: GameEventType.BuildUnit, payload: {unitId: uid, unitType: ut, ownerId: aiId, position: {x, y:0, z}}}, AI_USER);
                }
            }
            const idle = worldStateRef.current.units.filter(u => u.ownerId === aiId && !u.targetId);
            const eFort = worldStateRef.current.fortresses.find(f => f.ownerId === playerRef.current.id);
            if (idle.length > 0 && eFort) {
                idle.forEach(u => gameSvc.postEvent({type: GameEventType.MoveUnit, payload: {unitId: u.id, targetId: eFort.id}}, AI_USER));
            }
        }, []);

        const playerRef = useRef(player);
        const onGameOverRef = useRef(onGameOver);
        playerRef.current = player;
        onGameOverRef.current = onGameOver;

        const handleEvt = useCallback((evt) => {
            setWorldState(p => {
                let nu = [...p.units];
                let nf = [...p.fortresses];
                let nr = [...p.resources];

                switch(evt.type) {
                    case GameEventType.BuildUnit:
                        const {unitId, unitType, ownerId, position} = evt.payload;
                        const st = UNIT_STATS[unitType];
                        if (!nu.some(u => u.id === unitId)) {
                            nu.push({id: unitId, ownerId, type: unitType, position, targetId: null, health: st.health, maxHealth: st.health, lastAttack: 0});
                            if (ownerId !== playerRef.current.id) nr = nr.map((r,i) => i === ownerId ? r-st.cost : r);
                        }
                        break;
                    case GameEventType.MoveUnit:
                        nu = nu.map(u => u.id === evt.payload.unitId ? {...u, targetId: evt.payload.targetId} : u);
                        break;
                    case GameEventType.UnitAttack:
                        const {attackerId, targetId, damage} = evt.payload;
                        const att = nu.find(u => u.id === attackerId);
                        const now = Date.now();
                        if (att && now - (att.lastAttack || 0) > 1000) {
                            att.lastAttack = now;
                            let tu = nu.find(u => u.id === targetId);
                            let tf = nf.find(f => f.id === targetId);
                            if (tu) {
                                tu.health -= damage;
                                if (tu.health <= 0) { nu = nu.filter(u => u.id !== targetId); sndSvc.play('explosion'); debugLog('Unit destroyed'); }
                            } else if (tf) {
                                tf.health -= damage;
                                debugLog('Fortress HP: ' + tf.health);
                                if (tf.health <= 0) {
                                    const win = nf.find(f => f.id !== targetId)?.ownerId;
                                    if (win !== undefined && evt.sender.pubkey === playerRef.current.pubkey) {
                                        gameSvc.postEvent({type: GameEventType.GameOver, payload: {winnerId: win}}, playerRef.current);
                                    }
                                }
                            }
                        }
                        break;
                    case GameEventType.GameOver:
                        const msg = evt.payload.winnerId === playerRef.current.id ? "You Won!" : "You Lost.";
                        debugLog('Game Over: ' + msg);
                        alert(msg);
                        onGameOverRef.current();
                        break;
                }
                return {...p, units: nu, fortresses: nf, resources: nr};
            });
        }, []);

        useEffect(() => {
            debugLog(">>> Game useEffect: Starting game polling and AI");
            pollId.current = gameSvc.startPolling(handleEvt, 500);
            resId.current = setInterval(() => setWorldState(p => ({...p, resources: p.resources.map(r => r + RESOURCE_GEN_RATE)})), 1000);
            if (opponentRef.current.isAI) {
                aiId.current = setInterval(aiTick, 2000);
                debugLog(">>> AI opponent detected - started AI tick interval");
            }
            return () => {
                debugLog(">>> Game useEffect CLEANUP: Stopping game polling");
                if (pollId.current) gameSvc.stopPolling(pollId.current);
                if (resId.current) clearInterval(resId.current);
                if (aiId.current) clearInterval(aiId.current);
            };
        }, [handleEvt, aiTick]);

        return React.createElement('div', {className: 'relative w-full h-full'},
            React.createElement(GameBoard, {worldState, setWorldState, player, selectedUnit, onUnitSelect: handleUnitSel}),
            React.createElement(UI, {player, opponent, worldState, onBuildUnit: handleBuild, selectedUnit})
        );
    };

    const Lobby = ({onStartGame, userInfo}) => {
        debugLog(">>> Lobby component MOUNTED");

        const [status, setStatus] = useState('Looking for game...');
        const [waiting, setWaiting] = useState(false);
        const [countdown, setCountdown] = useState(30);
        const pollId = useRef(null);
        const aiTO = useRef(null);
        const cdInt = useRef(null);
        const waitingRef = useRef(false);
        const gameStartedRef = useRef(false);

        const cleanup = useCallback(() => {
            if (aiTO.current) { clearTimeout(aiTO.current); aiTO.current = null; }
            if (cdInt.current) { clearInterval(cdInt.current); cdInt.current = null; }
        }, []);

        const onStartGameRef = useRef(onStartGame);
        const userInfoRef = useRef(userInfo);
        onStartGameRef.current = onStartGame;
        userInfoRef.current = userInfo;

        const startGame = useCallback((self, opponent, role) => {
            if (gameStartedRef.current) {
                debugLog("Game already started - ignoring duplicate start request");
                return;
            }
            gameStartedRef.current = true;
            cleanup();
            onStartGameRef.current(self, opponent);
            debugLog("Started as " + role);
        }, [cleanup]);

        const handleEvt = useCallback((evt) => {
            if (gameStartedRef.current) return;
            if (evt.sender.pubkey === userInfoRef.current.pubkey) return;

            if (evt.type === GameEventType.JoinGame && !waitingRef.current) {
                setStatus('Game found! Starting...');
                const self = {...userInfoRef.current, id: 1, color: PLAYER_COLORS[1]};
                gameSvc.postEvent({type: GameEventType.StartGame, payload: {opponent: self}}, userInfoRef.current);
                startGame(self, evt.sender, "P1");
            } else if (evt.type === GameEventType.StartGame && waitingRef.current && evt.payload.opponent.pubkey === userInfoRef.current.pubkey) {
                setStatus('Game started!');
                const self = {...userInfoRef.current, id: 0, color: PLAYER_COLORS[0]};
                startGame(self, evt.sender, "P0");
            }
        }, [startGame]);

        useEffect(() => {
            debugLog(">>> Lobby useEffect: Starting matchmaking");
            pollId.current = gameSvc.startPolling(handleEvt);
            return () => {
                debugLog(">>> Lobby useEffect CLEANUP: Unmounting");
                if (pollId.current) gameSvc.stopPolling(pollId.current);
                cleanup();
            };
        }, [handleEvt, cleanup]);

        const join = () => {
            setStatus('Waiting for player...');
            setWaiting(true);
            waitingRef.current = true;
            setCountdown(30);
            gameSvc.postEvent({type: GameEventType.JoinGame, payload: {}}, userInfoRef.current);
            debugLog("Posted join - countdown starting");
            aiTO.current = setTimeout(() => {
                if (gameStartedRef.current) {
                    debugLog("Game already started - canceling AI timeout");
                    return;
                }
                setStatus('No players. Starting vs AI.');
                const self = {...userInfoRef.current, id: 0, color: PLAYER_COLORS[0]};
                startGame(self, AI_USER, "P0 vs AI");
            }, 30000);
            cdInt.current = setInterval(() => {
                setCountdown(p => {
                    const next = p <= 1 ? 0 : p - 1;
                    debugLog("Countdown: " + next);
                    return next;
                });
            }, 1000);
        };

        return React.createElement('div', {className: 'flex flex-col items-center justify-center h-screen bg-gray-900 text-white p-4'},
            React.createElement('div', {className: 'text-center bg-gray-800 p-4 rounded-lg shadow-2xl', style: {padding:'2.5rem', border:'1px solid rgba(59,130,246,0.3)'}},
                React.createElement('h1', {className: 'text-4xl font-bold mb-4 text-blue-400'}, 'Fortress Overlord'),
                React.createElement('p', {className: 'text-xl text-gray-300 mb-8'},
                    status,
                    waiting && React.createElement('span', {className: 'text-2xl', style: {fontFamily:'monospace', display:'block', marginTop:'1rem'}}, countdown)
                ),
                !waiting && React.createElement('button', {onClick: join, className: 'px-8 py-4 bg-green-600 text-white font-bold rounded-lg text-2xl transition'}, 'Find Game')
            ),
            React.createElement('div', {className: 'absolute bottom-4 text-sm text-gray-500'}, 'If no opponent found in 30s, you\'ll play vs AI.')
        );
    };

    const App = () => {
        const [gState, setGState] = useState(GameState.Lobby);
        const [audioStarted, setAudioStarted] = useState(false);
        const [userInfo, setUserInfo] = useState(null);
        const [player, setPlayer] = useState(null);
        const [opponent, setOpponent] = useState(null);
        const appGameStartedRef = useRef(false);

        useEffect(() => {
            (async () => {
                try {
                    const u = await window.bbs.getUserInfo();
                    setUserInfo(u);
                    debugLog('User: ' + (u.nickname || u.username));
                } catch (e) { debugLog('User fetch ERROR: ' + e.message); }
            })();
        }, []);

        const audioStartedRef = useRef(audioStarted);
        audioStartedRef.current = audioStarted;

        const handleStart = useCallback((self, opp) => {
            debugLog(">>> App.handleStart CALLED - appGameStartedRef: " + appGameStartedRef.current);
            if (appGameStartedRef.current) {
                debugLog(">>> App: BLOCKED - Game already started!");
                return;
            }
            appGameStartedRef.current = true;
            debugLog(">>> App: Starting game - setting state to GAME");

            if (!audioStartedRef.current) {
                debugLog(">>> App: Audio not started, starting audio first");
                window.Tone.start().then(() => {
                    setAudioStarted(true);
                    setPlayer(self);
                    setOpponent(opp);
                    setGState(GameState.Game);
                    debugLog(">>> App: State set to GAME (with audio)");
                });
            } else {
                debugLog(">>> App: Audio already started, setting state immediately");
                setPlayer(self);
                setOpponent(opp);
                setGState(GameState.Game);
                debugLog(">>> App: State set to GAME");
            }
        }, []);

        const handleOver = useCallback(() => {
            setGState(GameState.Lobby);
            setPlayer(null);
            setOpponent(null);
            appGameStartedRef.current = false;
            debugLog("Back to lobby - game can start again");
        }, []);

        const renderContent = () => {
            if (!userInfo) return React.createElement('div', {className: 'flex items-center justify-center h-screen text-xl'}, 'Loading...');
            if (!audioStarted) {
                return React.createElement('div', {className: 'flex flex-col items-center justify-center h-screen'},
                    React.createElement('h1', {className: 'text-4xl font-bold mb-4'}, 'Fortress Overlord'),
                    React.createElement('p', {className: 'text-lg mb-8'}, 'Real-time strategy game'),
                    React.createElement('button', {
                        onClick: () => window.Tone.start().then(() => { setAudioStarted(true); debugLog("Audio enabled"); }),
                        className: 'px-8 py-4 bg-blue-600 text-white font-bold rounded-lg text-xl transition'
                    }, 'Click to Start')
                );
            }
            if (gState === GameState.Lobby) return React.createElement(Lobby, {onStartGame: handleStart, userInfo});
            if (gState === GameState.Game && player && opponent) return React.createElement(Game, {player, opponent, onGameOver: handleOver});
            return React.createElement('div', {className: 'text-red-500'}, 'Error: Missing data');
        };

        return React.createElement('div', {className: 'w-full h-screen'}, renderContent());
    };

    debugLog("CHECKPOINT 7: Components defined");

    const rootEl = document.getElementById('applet-root');
    if (!rootEl) throw new Error('No applet-root element');

    debugLog("CHECKPOINT 8: Rendering React app");

    if (window.ReactDOM.createRoot) {
        const root = ReactDOM.createRoot(rootEl);
        root.render(React.createElement(App));
        debugLog("CHECKPOINT 9: App rendered with createRoot!");
    } else {
        ReactDOM.render(React.createElement(App), rootEl);
        debugLog("CHECKPOINT 9: App rendered with legacy render!");
    }

} catch (e) {
    console.error('ERROR:', e);
    const msg = 'ERROR: ' + e.message + '\n' + e.stack;
    document.getElementById('applet-root').innerHTML = '<div style="padding:20px;color:#ff4444;font-family:monospace;background:#1a2e40;"><h1>Error</h1><pre>' + msg + '</pre></div>';
    if (window.BBS_DEBUG_MODE) {
        const panel = document.getElementById('debug-panel');
        if (panel) {
            const err = document.createElement('div');
            err.textContent = 'ERROR: ' + e.message;
            err.style.color = '#ff4444';
            panel.appendChild(err);
        }
    }
}
})();
