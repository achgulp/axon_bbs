(async function() {
    'use strict';

    // ===== BBS API Helper =====
    if (!window.bbs) {
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
                        console.warn("BBS API: Not running in frame, simulating...");
                        resolve({});
                    }
                });
            },
            postEvent: function(eventData) { return this._postMessage('postEvent', eventData); },
            readEvents: function() { return this._postMessage('readEvents'); }
        };
        window.addEventListener('message', (event) => window.bbs._handleMessage(event));
    }

    // ===== Utility Functions =====
    const hexToRgba = (hex, alpha = 1) => {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    };

    const randomRange = (min, max) => Math.random() * (max - min) + min;

    // ===== HTML Setup =====
    document.body.innerHTML = `
        <div style="display: flex; gap: 20px; padding: 20px; font-family: Arial, sans-serif;">
            <!-- Left column: Brain visualization -->
            <div style="flex: 0 0 500px;">
                <h3 style="color: #ccc; margin-bottom: 10px;">🧠 Neural Activity</h3>
                <canvas id="brain-canvas" width="500" height="380"
                    style="border: 2px solid #333; border-radius: 10px; background: #0a0a0f;"></canvas>
                <div id="brain-status" style="margin-top: 10px; font-size: 12px; color: #888;">
                    Idle
                </div>
            </div>

            <!-- Right column: Query interface -->
            <div style="flex: 1; min-width: 400px;">
            <h2 style="color: #333; margin-bottom: 20px;">🤖 AI Router Test</h2>

            <div style="margin: 20px 0;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Query:</label>
                <textarea id="query-input" rows="3"
                    style="width: 100%; font-size: 16px; padding: 10px; border: 2px solid #ddd; border-radius: 5px;"
                    placeholder="Enter your question here..."></textarea>
            </div>

            <div style="margin: 20px 0;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Mode:</label>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button id="btn-consensus" style="padding: 12px 20px; font-size: 14px; border: 2px solid #007bff; border-radius: 5px; cursor: pointer; background: #f0f0f0;">
                        Consensus
                    </button>
                    <button id="btn-local" style="padding: 12px 20px; font-size: 14px; border: 2px solid #28a745; border-radius: 5px; cursor: pointer; background: #f0f0f0;">
                        Local Routing
                    </button>
                    <button id="btn-direct" style="padding: 12px 20px; font-size: 14px; border: 2px solid #ffc107; border-radius: 5px; cursor: pointer; background: #f0f0f0;">
                        Direct
                    </button>
                </div>
            </div>

            <div id="model-selector" style="margin: 20px 0; display: none;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Model:</label>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button id="btn-gemini" style="padding: 10px 18px; font-size: 14px; border: 2px solid #4285f4; border-radius: 5px; cursor: pointer; background: #f0f0f0;">
                        Gemini
                    </button>
                    <button id="btn-grok" style="padding: 10px 18px; font-size: 14px; border: 2px solid #000; border-radius: 5px; cursor: pointer; background: #f0f0f0;">
                        Grok
                    </button>
                    <button id="btn-claude" style="padding: 10px 18px; font-size: 14px; border: 2px solid #cc785c; border-radius: 5px; cursor: pointer; background: #f0f0f0;">
                        Claude
                    </button>
                    <button id="btn-local-model" style="padding: 10px 18px; font-size: 14px; border: 2px solid #6c757d; border-radius: 5px; cursor: pointer; background: #f0f0f0;">
                        Local
                    </button>
                </div>
            </div>

            <div style="margin: 20px 0;">
                <button id="submit-btn"
                    style="padding: 15px 40px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">
                    Submit Query
                </button>
            </div>

            <div id="status" style="margin: 20px 0; font-size: 14px; color: #666; font-weight: bold;">
                Ready
            </div>

            <div style="margin: 20px 0;">
                <label style="display: block; margin-bottom: 5px; font-weight: bold;">Answer:</label>
                <div id="answer"
                    style="padding: 15px; border: 2px solid #ddd; min-height: 100px; background: #f9f9f9; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word;">
                    (Answer will appear here)
                </div>
            </div>
            </div>
        </div>
    `;

    // ===== Brain Visualization System =====
    const canvas = document.getElementById('brain-canvas');
    const ctx = canvas.getContext('2d');
    const brainStatus = document.getElementById('brain-status');

    // Region configurations (adapted from full brain sim)
    const regionConfigs = {
        sensory: {
            pos: { x: 0.48, y: 0.32 }, size: 0.10,
            color: '#ff8844', label: 'Sensory'
        },
        frontal: {
            pos: { x: 0.78, y: 0.28 }, size: 0.14,
            color: '#00ffff', label: 'Frontal'
        },
        parietal: {
            pos: { x: 0.42, y: 0.18 }, size: 0.13,
            color: '#4488ff', label: 'Parietal'
        },
        temporal: {
            pos: { x: 0.68, y: 0.55 }, size: 0.12,
            color: '#00ff88', label: 'Temporal'
        },
        occipital: {
            pos: { x: 0.18, y: 0.38 }, size: 0.11,
            color: '#ff00ff', label: 'Occipital'
        },
        motor: {
            pos: { x: 0.58, y: 0.22 }, size: 0.10,
            color: '#ffff00', label: 'Motor'
        },
        hub: {
            pos: { x: 0.52, y: 0.42 }, size: 0.07,
            color: '#ffaa00', label: 'Hub'
        }
    };

    // Brain bounds (positioned within canvas)
    const brainBounds = {
        x: 50,
        y: 30,
        width: 400,
        height: 320
    };

    // Initialize neurons for each region
    const regions = {};
    const neurons = [];
    const connections = [];

    Object.keys(regionConfigs).forEach(regionId => {
        const config = regionConfigs[regionId];
        const centerX = brainBounds.x + brainBounds.width * config.pos.x;
        const centerY = brainBounds.y + brainBounds.height * config.pos.y;
        const radius = brainBounds.width * config.size;

        regions[regionId] = {
            id: regionId,
            x: centerX,
            y: centerY,
            radius: radius,
            color: config.color,
            label: config.label,
            activity: 0,
            neurons: []
        };

        // Create neurons for this region
        const neuronCount = regionId === 'hub' ? 15 : 25;
        for (let i = 0; i < neuronCount; i++) {
            const angle = (i / neuronCount) * Math.PI * 2;
            const dist = randomRange(0, radius * 0.8);
            const neuron = {
                id: `${regionId}_${i}`,
                regionId: regionId,
                x: centerX + Math.cos(angle) * dist,
                y: centerY + Math.sin(angle) * dist,
                activity: 0,
                radius: randomRange(2, 3.5)
            };
            neurons.push(neuron);
            regions[regionId].neurons.push(neuron);
        }
    });

    // Create connections between regions
    const regionPairs = [
        ['sensory', 'frontal'],
        ['frontal', 'parietal'],
        ['frontal', 'hub'],
        ['parietal', 'hub'],
        ['temporal', 'hub'],
        ['occipital', 'hub'],
        ['motor', 'hub'],
        ['hub', 'motor']
    ];

    regionPairs.forEach(([fromId, toId]) => {
        const fromRegion = regions[fromId];
        const toRegion = regions[toId];

        // Create a few sample connections
        for (let i = 0; i < 3; i++) {
            const fromNeuron = fromRegion.neurons[Math.floor(Math.random() * fromRegion.neurons.length)];
            const toNeuron = toRegion.neurons[Math.floor(Math.random() * toRegion.neurons.length)];

            connections.push({
                from: fromNeuron,
                to: toNeuron,
                activity: 0,
                pulse: { active: false, phase: 0 },
                color: fromRegion.color
            });
        }
    });

    // Draw realistic brain outline
    function drawBrainOutline() {
        const { x, y, width, height } = brainBounds;

        ctx.strokeStyle = '#444';
        ctx.lineWidth = 2;

        // Detailed cerebrum outline (sagittal view)
        ctx.beginPath();

        // Start at frontal lobe base (right side)
        ctx.moveTo(x + width * 0.88, y + height * 0.60);

        // Frontal lobe curves
        ctx.bezierCurveTo(
            x + width * 0.95, y + height * 0.55,
            x + width * 1.00, y + height * 0.48,
            x + width * 0.99, y + height * 0.40
        );
        ctx.bezierCurveTo(
            x + width * 1.00, y + height * 0.32,
            x + width * 0.96, y + height * 0.24,
            x + width * 0.90, y + height * 0.18
        );
        ctx.bezierCurveTo(
            x + width * 0.85, y + height * 0.12,
            x + width * 0.78, y + height * 0.08,
            x + width * 0.70, y + height * 0.05
        );

        // Superior frontal gyrus and motor/sensory peaks
        ctx.bezierCurveTo(
            x + width * 0.65, y + height * 0.03,
            x + width * 0.58, y + height * 0.03,
            x + width * 0.52, y + height * 0.04
        );
        ctx.bezierCurveTo(
            x + width * 0.48, y + height * 0.02,
            x + width * 0.42, y + height * 0.03,
            x + width * 0.35, y + height * 0.06
        );

        // Parietal lobe curve
        ctx.bezierCurveTo(
            x + width * 0.28, y + height * 0.09,
            x + width * 0.18, y + height * 0.15,
            x + width * 0.10, y + height * 0.25
        );

        // Occipital lobe
        ctx.bezierCurveTo(
            x + width * 0.02, y + height * 0.35,
            x + width * 0.01, y + height * 0.45,
            x + width * 0.05, y + height * 0.55
        );

        // Under-occipital area
        ctx.bezierCurveTo(
            x + width * 0.10, y + height * 0.62,
            x + width * 0.20, y + height * 0.65,
            x + width * 0.30, y + height * 0.64
        );

        // Temporal lobe
        ctx.bezierCurveTo(
            x + width * 0.35, y + height * 0.68,
            x + width * 0.40, y + height * 0.75,
            x + width * 0.50, y + height * 0.78
        );
        ctx.bezierCurveTo(
            x + width * 0.65, y + height * 0.82,
            x + width * 0.82, y + height * 0.78,
            x + width * 0.90, y + height * 0.68
        );

        // Close to frontal base
        ctx.bezierCurveTo(
            x + width * 0.92, y + height * 0.65,
            x + width * 0.90, y + height * 0.62,
            x + width * 0.88, y + height * 0.60
        );

        ctx.stroke();

        // Add cerebellum (bottom-right bump)
        ctx.beginPath();
        ctx.moveTo(x + width * 0.70, y + height * 0.65);
        ctx.bezierCurveTo(
            x + width * 0.75, y + height * 0.68,
            x + width * 0.85, y + height * 0.70,
            x + width * 0.95, y + height * 0.75
        );
        ctx.bezierCurveTo(
            x + width * 1.00, y + height * 0.82,
            x + width * 0.95, y + height * 0.92,
            x + width * 0.85, y + height * 0.96
        );
        ctx.bezierCurveTo(
            x + width * 0.75, y + height * 0.98,
            x + width * 0.65, y + height * 0.95,
            x + width * 0.60, y + height * 0.88
        );
        ctx.bezierCurveTo(
            x + width * 0.58, y + height * 0.80,
            x + width * 0.62, y + height * 0.72,
            x + width * 0.70, y + height * 0.65
        );
        ctx.stroke();
    }

    // Render brain visualization
    function renderBrain() {
        // Clear canvas
        ctx.fillStyle = '#0a0a0f';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw brain outline
        drawBrainOutline();

        // Draw connections with activity
        connections.forEach(conn => {
            if (conn.activity > 0.03 || conn.pulse.active) {
                const alpha = Math.max(conn.activity, conn.pulse.active ? 0.3 : 0);
                ctx.strokeStyle = hexToRgba(conn.color, alpha);
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(conn.from.x, conn.from.y);
                ctx.lineTo(conn.to.x, conn.to.y);
                ctx.stroke();

                // Draw traveling pulse
                if (conn.pulse.active) {
                    const t = conn.pulse.phase;
                    const px = conn.from.x + (conn.to.x - conn.from.x) * t;
                    const py = conn.from.y + (conn.to.y - conn.from.y) * t;

                    ctx.fillStyle = hexToRgba(conn.color, 0.9);
                    ctx.beginPath();
                    ctx.arc(px, py, 3, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
        });

        // Draw region ambient glow
        Object.values(regions).forEach(region => {
            if (region.activity > 0.05) {
                const glowRadius = region.radius * (1.2 + region.activity * 0.5);
                const gradient = ctx.createRadialGradient(
                    region.x, region.y, 0,
                    region.x, region.y, glowRadius
                );
                gradient.addColorStop(0, hexToRgba(region.color, region.activity * 0.15));
                gradient.addColorStop(0.5, hexToRgba(region.color, region.activity * 0.05));
                gradient.addColorStop(1, 'transparent');

                ctx.fillStyle = gradient;
                ctx.beginPath();
                ctx.arc(region.x, region.y, glowRadius, 0, Math.PI * 2);
                ctx.fill();
            }
        });

        // Draw neurons
        neurons.forEach(neuron => {
            const baseAlpha = 0.3;
            const activeAlpha = 0.3 + neuron.activity * 0.7;
            const regionColor = regions[neuron.regionId].color;

            // Glow if active
            if (neuron.activity > 0.1) {
                ctx.fillStyle = hexToRgba(regionColor, neuron.activity * 0.3);
                ctx.beginPath();
                ctx.arc(neuron.x, neuron.y, neuron.radius + 3, 0, Math.PI * 2);
                ctx.fill();
            }

            // Neuron body
            ctx.fillStyle = hexToRgba(regionColor, activeAlpha);
            ctx.beginPath();
            ctx.arc(neuron.x, neuron.y, neuron.radius, 0, Math.PI * 2);
            ctx.fill();
        });

        // Draw labels
        ctx.fillStyle = '#888';
        ctx.font = '11px Arial';
        ctx.textAlign = 'center';
        Object.values(regions).forEach(region => {
            ctx.fillText(region.label, region.x, region.y + region.radius + 15);
        });

        // Decay activity
        Object.values(regions).forEach(region => {
            region.activity *= 0.95;
        });
        neurons.forEach(neuron => {
            neuron.activity *= 0.92;
        });
        connections.forEach(conn => {
            conn.activity *= 0.9;
            if (conn.pulse.active) {
                conn.pulse.phase += 0.012;
                if (conn.pulse.phase >= 1) {
                    conn.pulse.active = false;
                    conn.pulse.phase = 0;
                }
            }
        });

        requestAnimationFrame(renderBrain);
    }

    // Stimulate a brain region
    function stimulateRegion(regionName, intensity = 1.0) {
        if (regions[regionName]) {
            const region = regions[regionName];
            region.activity = Math.min(1.0, intensity);

            // Activate neurons in region
            region.neurons.forEach(neuron => {
                neuron.activity = Math.min(1.0, intensity + Math.random() * 0.2);
            });

            // Activate connections from this region
            connections.forEach(conn => {
                if (conn.from.regionId === regionName) {
                    conn.activity = intensity * 0.7;
                    conn.pulse.active = true;
                    conn.pulse.phase = 0;
                }
            });

            brainStatus.textContent = `Active: ${region.label} (${(intensity * 100).toFixed(0)}%)`;
        }
    }

    // Reset brain activity
    function resetBrain() {
        Object.values(regions).forEach(region => region.activity = 0);
        neurons.forEach(neuron => neuron.activity = 0);
        connections.forEach(conn => {
            conn.activity = 0;
            conn.pulse.active = false;
            conn.pulse.phase = 0;
        });
        brainStatus.textContent = 'Idle';
    }

    // Start rendering loop
    renderBrain();

    // ===== State =====
    let selectedMode = 'direct';
    let selectedModel = 'gemini';
    let currentQueryId = null;
    let pollInterval = null;

    // ===== UI Elements =====
    const queryInput = document.getElementById('query-input');
    const submitBtn = document.getElementById('submit-btn');
    const statusDiv = document.getElementById('status');
    const answerDiv = document.getElementById('answer');
    const modelSelector = document.getElementById('model-selector');

    // Mode buttons
    const btnConsensus = document.getElementById('btn-consensus');
    const btnLocal = document.getElementById('btn-local');
    const btnDirect = document.getElementById('btn-direct');

    // Model buttons
    const btnGemini = document.getElementById('btn-gemini');
    const btnGrok = document.getElementById('btn-grok');
    const btnClaude = document.getElementById('btn-claude');
    const btnLocalModel = document.getElementById('btn-local-model');

    // ===== Mode Selection =====
    function selectMode(mode) {
        selectedMode = mode;

        [btnConsensus, btnLocal, btnDirect].forEach(btn => {
            btn.style.background = '#f0f0f0';
            btn.style.color = '#000';
            btn.style.fontWeight = 'normal';
        });

        if (mode === 'consensus') {
            btnConsensus.style.background = '#007bff';
            btnConsensus.style.color = 'white';
            btnConsensus.style.fontWeight = 'bold';
            modelSelector.style.display = 'none';
        } else if (mode === 'local') {
            btnLocal.style.background = '#28a745';
            btnLocal.style.color = 'white';
            btnLocal.style.fontWeight = 'bold';
            modelSelector.style.display = 'none';
        } else {
            btnDirect.style.background = '#ffc107';
            btnDirect.style.color = '#000';
            btnDirect.style.fontWeight = 'bold';
            modelSelector.style.display = 'block';
        }
    }

    btnConsensus.addEventListener('click', () => selectMode('consensus'));
    btnLocal.addEventListener('click', () => selectMode('local'));
    btnDirect.addEventListener('click', () => selectMode('direct'));

    // ===== Model Selection =====
    function selectModel(model) {
        selectedModel = model;

        [btnGemini, btnGrok, btnClaude, btnLocalModel].forEach(btn => {
            btn.style.background = '#f0f0f0';
            btn.style.color = '#000';
            btn.style.fontWeight = 'normal';
        });

        const btnMap = {
            'gemini': btnGemini,
            'grok': btnGrok,
            'claude': btnClaude,
            'local': btnLocalModel
        };

        const colorMap = {
            'gemini': '#4285f4',
            'grok': '#000',
            'claude': '#cc785c',
            'local': '#6c757d'
        };

        btnMap[model].style.background = colorMap[model];
        btnMap[model].style.color = 'white';
        btnMap[model].style.fontWeight = 'bold';
    }

    btnGemini.addEventListener('click', () => selectModel('gemini'));
    btnGrok.addEventListener('click', () => selectModel('grok'));
    btnClaude.addEventListener('click', () => selectModel('claude'));
    btnLocalModel.addEventListener('click', () => selectModel('local'));

    // ===== Submit Query =====
    submitBtn.addEventListener('click', async () => {
        const query = queryInput.value.trim();
        if (!query) {
            alert('Please enter a query');
            return;
        }

        currentQueryId = generateUUID();

        const queryMsg = {
            query_id: currentQueryId,
            query: query,
            mode: selectedMode,
            model: selectedMode === 'direct' ? selectedModel : null
        };

        try {
            // Reset brain visualization
            resetBrain();

            // Post query
            await bbs.postEvent({
                subject: 'RouterQuery',
                body: JSON.stringify(queryMsg)
            });

            // Update UI
            submitBtn.disabled = true;
            submitBtn.style.background = '#6c757d';
            statusDiv.textContent = 'Processing... (0s)';
            answerDiv.textContent = 'Waiting for response...';

            // Start polling
            startPolling();
        } catch (error) {
            alert('Failed to submit query: ' + error.message);
            console.error('Submit error:', error);
        }
    });

    // ===== Polling =====
    function startPolling() {
        let elapsed = 0;

        pollInterval = setInterval(async () => {
            elapsed += 2;
            statusDiv.textContent = `Processing... (${elapsed}s)`;

            try {
                // Read events
                const eventsData = await bbs.readEvents();
                const events = Array.isArray(eventsData) ? eventsData : [];

                // Process stage updates for brain visualization
                const stageUpdates = events.filter(e => e.subject === 'RouterStageUpdate');
                for (const update of stageUpdates) {
                    try {
                        const stageData = JSON.parse(update.body);
                        if (stageData.query_id === currentQueryId) {
                            // Stimulate the corresponding brain region
                            stimulateRegion(stageData.region, stageData.activity);
                        }
                    } catch (e) {
                        console.error('Failed to parse stage update:', e);
                    }
                }

                const responses = events.filter(e =>
                    e.subject === 'RouterResponse'
                );

                if (responses.length > 0) {
                    for (const resp of responses) {
                        try {
                            const responseBody = JSON.parse(resp.body);

                            if (responseBody.query_id === currentQueryId) {
                                displayResponse(responseBody);
                                stopPolling();
                                return;
                            }
                        } catch (e) {
                            console.error('Failed to parse response:', e);
                        }
                    }
                }

                // Timeout after 2 minutes
                if (elapsed > 120) {
                    statusDiv.textContent = 'Timeout - No response received';
                    answerDiv.textContent = 'Query timed out. The agent may be offline or the query took too long.';
                    stopPolling();
                }
            } catch (error) {
                console.error('Poll error:', error);
            }
        }, 2000);
    }

    function stopPolling() {
        clearInterval(pollInterval);
        submitBtn.disabled = false;
        submitBtn.style.background = '#007bff';
    }

    // ===== Display Response =====
    function displayResponse(response) {
        if (response.status === 'success') {
            const time = response.metadata.processing_time.toFixed(1);
            statusDiv.textContent = `✅ Complete (${time}s)`;
            statusDiv.style.color = '#28a745';

            let html = `<strong>${response.answer}</strong>`;
            html += `\n\n━━━━━━━━━━━━━━━━━━━━━━`;
            html += `\n📊 Metadata:`;
            html += `\n  Mode: ${response.metadata.mode}`;

            if (response.metadata.model) {
                html += `\n  Model: ${response.metadata.model}`;
            }

            if (response.metadata.provider) {
                html += `\n  Provider: ${response.metadata.provider}`;
            }

            if (response.metadata.speed) {
                html += `\n  Speed: ${response.metadata.speed.toFixed(1)} t/s`;
            }

            html += `\n  Processing Time: ${time}s`;

            answerDiv.textContent = html;
        } else {
            statusDiv.textContent = `❌ Error: ${response.status}`;
            statusDiv.style.color = '#dc3545';
            answerDiv.textContent = response.error || 'Unknown error';
        }
    }

    // ===== Utilities =====
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // ===== Initialize =====
    selectMode('direct');
    selectModel('gemini');

    console.log('✅ AI Router Test applet loaded (with full brain visualization)');
})();
