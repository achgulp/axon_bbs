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

    // ===== HTML Setup =====
    document.body.innerHTML = `
        <div style="padding: 20px; font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
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
    `;

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

        // Reset all mode buttons
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

        // Reset all model buttons
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
                // API returns array directly
                const events = Array.isArray(eventsData) ? eventsData : [];
                const responses = events.filter(e =>
                    e.subject === 'RouterResponse'
                );

                if (responses.length > 0) {
                    // Find response for our query
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

    console.log('✅ AI Router Test applet loaded');
})();
