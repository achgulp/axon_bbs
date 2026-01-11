/**
 * Network module
 * Handles neurons, connections, regions, and signal propagation
 *
 * OPTIMIZED: Uses connection "activity glow" instead of tracking individual
 * signal particles - much more performant with many connections.
 */

// ============================================
// NEURON CLASS
// ============================================
class Neuron {
    constructor(id, x, y, regionId) {
        this.id = id;
        this.x = x;
        this.y = y;
        this.regionId = regionId;
        this.radius = Utils.randomRange(CONFIG.neurons.minRadius, CONFIG.neurons.maxRadius);

        // State
        this.activity = 0;          // 0 to 1 (visual glow)
        this.potential = 0;         // Accumulated input
        this.threshold = 0.5;       // Firing threshold
        this.refractory = 0;        // Refractory period counter
        this.justFired = false;     // Did we fire this frame?

        // Connections (populated after creation)
        this.outgoing = [];
        this.incoming = [];
    }

    /**
     * Receive input from a connection
     */
    receiveInput(amount, weight = 1) {
        if (this.refractory > 0) return;
        this.potential += amount * weight;
    }

    /**
     * Update neuron state - returns true if fired
     */
    update() {
        // Track if we fired THIS frame
        this.justFired = false;

        // Handle refractory period
        if (this.refractory > 0) {
            this.refractory--;
        }

        // Check firing condition
        if (this.potential >= this.threshold && this.refractory <= 0) {
            this.justFired = true;
            this.activity = 0.85;  // Start lower, not full blast
            this.refractory = 5;
            this.potential = 0;
        } else {
            // Smooth activity decay
            this.activity *= 0.88;
        }

        // Decay potential
        this.potential *= (1 - CONFIG.neurons.decayRate);

        return this.justFired;
    }

    /**
     * Manually stimulate
     */
    stimulate(strength = 1) {
        this.potential += strength;
    }
}

// ============================================
// CONNECTION CLASS (OPTIMIZED - no individual signals)
// With Oja's rule for online Hebbian learning
// ============================================
class Connection {
    constructor(from, to, strength = 0.5) {
        this.id = Utils.generateId('conn_');
        this.from = from;
        this.to = to;

        // Synaptic weight (learnable) - distinct from signal strength
        this.weight = strength + (Math.random() - 0.5) * 0.1; // Small random variation
        this.initialWeight = this.weight; // Track for visualization
        this.minWeight = 0.01;
        this.maxWeight = 1.0;

        // Activity level (0-1) - controls glow intensity
        // No more individual signal tracking!
        this.activity = 0;

        // Pulse effect - when a signal is sent, this creates a "wave"
        this.pulsePhase = 0;      // 0 to 1, represents wave position
        this.pulseActive = false;

        // Learning tracking
        this.lastWeightChange = 0; // For visualization of learning events
        this.eligibility = 0;      // Neuromodulated trace
    }

    /**
     * Trigger a pulse along this connection (replaces addSignal)
     */
    pulse(strength = 1) {
        this.activity = Math.min(1, this.activity + strength * 0.3);  // Reduced accumulation
        this.pulseActive = true;
        this.pulsePhase = 0;
    }

    /**
     * Update connection state
     */
    update(speedMultiplier = 1) {
        let delivered = false;

        // Update eligibility trace (decays naturally)
        const pre = this.from.activity;
        const post = this.to.activity;
        // Trace is high when pre- and post-synaptic neurons are active together
        this.eligibility = this.eligibility * 0.95 + (pre * post);
        this.eligibility = Math.min(5, this.eligibility); // Cap it

        // Update pulse travel
        if (this.pulseActive) {
            this.pulsePhase += CONFIG.signals.speed * speedMultiplier;

            // Pulse arrived at destination
            if (this.pulsePhase >= 1) {
                delivered = true;
                this.pulseActive = false;
                this.pulsePhase = 0;
            }
        }

        // Faster decay - no lingering trails
        this.activity *= 0.9;

        // Decay lastWeightChange for visualization
        this.lastWeightChange *= 0.95;

        return delivered;
    }

    /**
     * Apply Reward-Modulated Learning
     * This is more "natural" and effective than pure unsupervised Oja's rule
     * Δw = η * Reward * Eligibility
     */
    applyReward(reward, learningRate) {
        if (this.eligibility < 0.01) return;

        const deltaW = learningRate * reward * this.eligibility;
        this.weight += deltaW;
        this.lastWeightChange = Math.abs(deltaW) * 20;

        // Clamp weights to valid range
        this.weight = Math.max(this.minWeight, Math.min(this.maxWeight, this.weight));
        
        // Faster eligibility decay after update
        this.eligibility *= 0.5;
    }

    /**
     * Apply Oja's learning rule
     * Δw = η * y * (x - y * w)
     * This naturally normalizes weights and prevents explosion
     */
    applyOjaLearning(learningRate, decayRate) {
        const pre = this.from.activity;  // x: presynaptic activity
        const post = this.to.activity;   // y: postsynaptic activity

        // Only learn when there's meaningful activity
        if (pre > 0.1 && post > 0.1) {
            // Oja's rule: Δw = η * y * (x - y * w)
            const deltaW = learningRate * post * (pre - post * this.weight);
            // In reward-modulated mode, we use Oja's primarily for normalization/decay
            // so we scale it down relative to the reward signal
            this.weight += deltaW * 0.2; 
        }

        // Apply slow decay toward initial weight when inactive
        if (pre < 0.05 && post < 0.05) {
            const decay = (this.weight - this.initialWeight) * decayRate * 0.1;
            this.weight -= decay;
        }

        // Clamp weights to valid range
        this.weight = Math.max(this.minWeight, Math.min(this.maxWeight, this.weight));
    }

    /**
     * Get weight change from initial (for visualization)
     */
    getWeightDelta() {
        return this.weight - this.initialWeight;
    }

    /**
     * Reset weight to initial value
     */
    resetWeight() {
        this.weight = this.initialWeight;
        this.lastWeightChange = 0;
    }

    /**
     * Get pulse position for rendering (if active)
     */
    getPulsePosition() {
        if (!this.pulseActive) return null;

        // Ease the movement for nicer visual
        const t = Utils.easeInOut(this.pulsePhase);
        return {
            x: Utils.lerp(this.from.x, this.to.x, t),
            y: Utils.lerp(this.from.y, this.to.y, t),
            intensity: 1 - this.pulsePhase * 0.5  // Fade as it travels
        };
    }
}

// ============================================
// REGION CLASS
// ============================================
class Region {
    constructor(id, config, brainRenderer) {
        this.id = id;
        this.config = config;
        this.brainRenderer = brainRenderer;

        this.x = 0;
        this.y = 0;
        this.radius = 0;
        this.neurons = [];
        this.totalActivity = 0;

        this.initialize();
    }

    initialize() {
        const pos = this.brainRenderer.getAbsolutePosition(
            this.config.relativePosition.x,
            this.config.relativePosition.y
        );
        this.x = pos.x;
        this.y = pos.y;
        this.radius = Math.min(
            this.brainRenderer.bounds.width,
            this.brainRenderer.bounds.height
        ) * this.config.relativeSize;

        this.generateNeurons();
    }

    generateNeurons() {
        const count = CONFIG.neurons.countPerRegion;

        for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const r = Math.random() * this.radius * 0.85;

            const x = this.x + Math.cos(angle) * r;
            const y = this.y + Math.sin(angle) * r;

            if (this.brainRenderer.isPointInBrain(x, y)) {
                const neuron = new Neuron(`${this.id}_${i}`, x, y, this.id);
                this.neurons.push(neuron);
            }
        }
    }

    update() {
        this.totalActivity = 0;
        for (const neuron of this.neurons) {
            neuron.update();
            this.totalActivity += neuron.activity;
        }
        if (this.neurons.length > 0) {
            this.totalActivity /= this.neurons.length;
        }
    }

    getActivityPercent() {
        return Math.round(this.totalActivity * 100);
    }

    stimulate(strength = 1, count = 5) {
        const shuffled = Utils.shuffle([...this.neurons]);
        const toStimulate = shuffled.slice(0, Math.min(count, shuffled.length));
        for (const neuron of toStimulate) {
            neuron.stimulate(strength);
        }
    }

    recalculate() {
        const pos = this.brainRenderer.getAbsolutePosition(
            this.config.relativePosition.x,
            this.config.relativePosition.y
        );
        const oldX = this.x;
        const oldY = this.y;
        const oldRadius = this.radius;

        this.x = pos.x;
        this.y = pos.y;
        this.radius = Math.min(
            this.brainRenderer.bounds.width,
            this.brainRenderer.bounds.height
        ) * this.config.relativeSize;

        for (const neuron of this.neurons) {
            const relX = (neuron.x - oldX) / oldRadius;
            const relY = (neuron.y - oldY) / oldRadius;
            neuron.x = this.x + relX * this.radius;
            neuron.y = this.y + relY * this.radius;
        }
    }
}

// ============================================
// CENTRAL HUB CLASS
// ============================================
class CentralHub {
    constructor(config, brainRenderer) {
        this.config = config;
        this.brainRenderer = brainRenderer;
        this.x = 0;
        this.y = 0;
        this.radius = 0;
        this.neurons = [];
        this.state = [0, 0, 0, 0];

        this.initialize();
    }

    initialize() {
        const pos = this.brainRenderer.getAbsolutePosition(
            this.config.relativePosition.x,
            this.config.relativePosition.y
        );
        this.x = pos.x;
        this.y = pos.y;
        this.radius = Math.min(
            this.brainRenderer.bounds.width,
            this.brainRenderer.bounds.height
        ) * this.config.relativeSize;

        this.generateNeurons();
    }

    generateNeurons() {
        const count = 15;
        for (let i = 0; i < count; i++) {
            const angle = Math.random() * Math.PI * 2;
            const r = Math.random() * this.radius * 0.8;
            const neuron = new Neuron(
                `hub_${i}`,
                this.x + Math.cos(angle) * r,
                this.y + Math.sin(angle) * r,
                'hub'
            );
            this.neurons.push(neuron);
        }
    }

    aggregate(regions) {
        const regionIds = Object.keys(regions);
        this.state = [0, 0, 0, 0];
        regionIds.forEach((id, index) => {
            this.state[index % 4] += regions[id].totalActivity;
        });
        this.state = this.state.map(v => Math.min(1, v / 2));
    }

    update() {
        for (const neuron of this.neurons) {
            neuron.update();
        }
    }

    recalculate() {
        const pos = this.brainRenderer.getAbsolutePosition(
            this.config.relativePosition.x,
            this.config.relativePosition.y
        );
        const oldX = this.x;
        const oldY = this.y;
        const oldRadius = this.radius;

        this.x = pos.x;
        this.y = pos.y;
        this.radius = Math.min(
            this.brainRenderer.bounds.width,
            this.brainRenderer.bounds.height
        ) * this.config.relativeSize;

        for (const neuron of this.neurons) {
            const relX = (neuron.x - oldX) / oldRadius;
            const relY = (neuron.y - oldY) / oldRadius;
            neuron.x = this.x + relX * this.radius;
            neuron.y = this.y + relY * this.radius;
        }
    }
}

// ============================================
// NETWORK CLASS
// ============================================
class Network {
    constructor(brainRenderer) {
        this.brainRenderer = brainRenderer;
        this.regions = {};
        this.hub = null;
        this.connections = [];
        this.allNeurons = [];

        // Statistics
        this.stats = {
            totalSignals: 0,
            firingRate: 0,
            activeNeurons: 0,
            signalsThisSecond: 0,
            lastSecond: Date.now()
        };

        this.initialize();
    }

    initialize() {
        for (const [id, config] of Object.entries(CONFIG.regions)) {
            this.regions[id] = new Region(id, config, this.brainRenderer);
        }
        this.hub = new CentralHub(CONFIG.hub, this.brainRenderer);
        this.collectNeurons();
        this.createConnections();
    }

    collectNeurons() {
        this.allNeurons = [];
        for (const region of Object.values(this.regions)) {
            this.allNeurons.push(...region.neurons);
        }
        this.allNeurons.push(...this.hub.neurons);
    }

    createConnections() {
        this.connections = [];

        // Intra-region connections (sparse)
        for (const region of Object.values(this.regions)) {
            this.createIntraRegionConnections(region);
        }

        // Hub connections
        this.createHubConnections();

        // Inter-region connections (very sparse)
        this.createInterRegionConnections();
    }

    createIntraRegionConnections(region) {
        const neurons = region.neurons;
        const prob = CONFIG.connections.intraRegionProbability;

        for (let i = 0; i < neurons.length; i++) {
            for (let j = 0; j < neurons.length; j++) {
                if (i !== j && Math.random() < prob) {
                    const conn = new Connection(neurons[i], neurons[j]);
                    this.connections.push(conn);
                    neurons[i].outgoing.push(conn);
                    neurons[j].incoming.push(conn);
                }
            }
        }
    }

    createHubConnections() {
        const hubNeurons = this.hub.neurons;
        const prob = CONFIG.connections.hubConnectionProbability;

        for (const region of Object.values(this.regions)) {
            for (const neuron of region.neurons) {
                if (Math.random() < prob) {
                    const hubNeuron = hubNeurons[Utils.randomInt(0, hubNeurons.length - 1)];
                    const conn = new Connection(neuron, hubNeuron);
                    this.connections.push(conn);
                    neuron.outgoing.push(conn);
                    hubNeuron.incoming.push(conn);
                }
                if (Math.random() < prob) {
                    const hubNeuron = hubNeurons[Utils.randomInt(0, hubNeurons.length - 1)];
                    const conn = new Connection(hubNeuron, neuron);
                    this.connections.push(conn);
                    hubNeuron.outgoing.push(conn);
                    neuron.incoming.push(conn);
                }
            }
        }

        // Hub internal
        for (let i = 0; i < hubNeurons.length; i++) {
            for (let j = 0; j < hubNeurons.length; j++) {
                if (i !== j && Math.random() < 0.25) {
                    const conn = new Connection(hubNeurons[i], hubNeurons[j]);
                    this.connections.push(conn);
                    hubNeurons[i].outgoing.push(conn);
                    hubNeurons[j].incoming.push(conn);
                }
            }
        }
    }

    createInterRegionConnections() {
        const regionIds = Object.keys(this.regions);
        const prob = CONFIG.connections.interRegionProbability;

        for (let i = 0; i < regionIds.length; i++) {
            for (let j = i + 1; j < regionIds.length; j++) {
                const region1 = this.regions[regionIds[i]];
                const region2 = this.regions[regionIds[j]];

                for (const n1 of region1.neurons) {
                    for (const n2 of region2.neurons) {
                        if (Math.random() < prob) {
                            const conn = new Connection(n1, n2);
                            this.connections.push(conn);
                            n1.outgoing.push(conn);
                            n2.incoming.push(conn);
                        }
                    }
                }
            }
        }
    }

    /**
     * Apply a global reward signal to the network
     */
    applyGlobalRewardSignal(reward, learningRate = 0.05) {
        for (const conn of this.connections) {
            conn.applyReward(reward, learningRate);
        }
    }

    /**
     * Main update loop - OPTIMIZED
     * Now includes online learning via Oja's rule
     */
    update(speedMultiplier = 1, learningEnabled = true, learningRate = 0.02, decayRate = 0.01) {
        // Update connections - deliver pulses that arrived
        for (const conn of this.connections) {
            const delivered = conn.update(speedMultiplier);
            if (delivered) {
                conn.to.receiveInput(0.8, conn.weight);  // Weight affects signal strength
                this.stats.signalsThisSecond++;
            }
        }

        // Update all regions
        for (const region of Object.values(this.regions)) {
            region.update();
        }

        // LATERAL INHIBITION (Natural competition in Motor region)
        // This forces OUT-1 and OUT-2 to compete
        const motor = this.regions.motor;
        if (motor && motor.neurons.length > 0) {
            const midpoint = Math.floor(motor.neurons.length / 2);
            let out1Sum = 0;
            let out2Sum = 0;
            for (let i = 0; i < midpoint; i++) out1Sum += motor.neurons[i].activity;
            for (let i = midpoint; i < motor.neurons.length; i++) out2Sum += motor.neurons[i].activity;

            // Simple winner-takes-more inhibition
            const inhibitionStrength = 0.1;
            if (out1Sum > out2Sum) {
                for (let i = midpoint; i < motor.neurons.length; i++) {
                    motor.neurons[i].activity *= (1 - inhibitionStrength);
                    motor.neurons[i].potential *= (1 - inhibitionStrength);
                }
            } else if (out2Sum > out1Sum) {
                for (let i = 0; i < midpoint; i++) {
                    motor.neurons[i].activity *= (1 - inhibitionStrength);
                    motor.neurons[i].potential *= (1 - inhibitionStrength);
                }
            }
        }

        // Check for neurons that fired after update/inhibition
        for (const region of Object.values(this.regions)) {
            for (const neuron of region.neurons) {
                if (neuron.justFired) {
                    // Neuron fired - pulse all outgoing connections
                    for (const conn of neuron.outgoing) {
                        conn.pulse(1);
                        this.stats.totalSignals++;
                    }
                }
            }
        }

        // Update hub
        this.hub.update();
        this.hub.aggregate(this.regions);

        for (const neuron of this.hub.neurons) {
            if (neuron.justFired) {
                for (const conn of neuron.outgoing) {
                    conn.pulse(1);
                    this.stats.totalSignals++;
                }
            }
        }

        // Subtle spontaneous activity - occasional random firing
        if (Math.random() < 0.008) {  // Reduced from 2% to 0.8%
            const regions = Object.values(this.regions);
            const randomRegion = regions[Math.floor(Math.random() * regions.length)];
            if (randomRegion.neurons.length > 0) {
                const randomNeuron = randomRegion.neurons[Math.floor(Math.random() * randomRegion.neurons.length)];
                randomNeuron.stimulate(0.4);  // Reduced strength
            }
        }

        // Apply online learning (Oja's rule) to all connections
        if (learningEnabled) {
            for (const conn of this.connections) {
                conn.applyOjaLearning(learningRate, decayRate);
            }
        }

        this.updateStats();
    }

    /**
     * Reset all connection weights to initial values
     */
    resetWeights() {
        for (const conn of this.connections) {
            conn.resetWeight();
        }
    }

    /**
     * Get average weight change across all connections
     */
    getAverageWeightDelta() {
        if (this.connections.length === 0) return 0;
        let total = 0;
        for (const conn of this.connections) {
            total += Math.abs(conn.getWeightDelta());
        }
        return total / this.connections.length;
    }

    /**
     * Get weight statistics for visualization
     */
    getWeightStats() {
        let minWeight = 1, maxWeight = 0, avgWeight = 0;
        let strengthened = 0, weakened = 0;

        for (const conn of this.connections) {
            minWeight = Math.min(minWeight, conn.weight);
            maxWeight = Math.max(maxWeight, conn.weight);
            avgWeight += conn.weight;

            const delta = conn.getWeightDelta();
            if (delta > 0.01) strengthened++;
            else if (delta < -0.01) weakened++;
        }

        avgWeight /= this.connections.length;

        return { minWeight, maxWeight, avgWeight, strengthened, weakened };
    }

    updateStats() {
        const now = Date.now();
        if (now - this.stats.lastSecond >= 1000) {
            this.stats.firingRate = this.stats.signalsThisSecond;
            this.stats.signalsThisSecond = 0;
            this.stats.lastSecond = now;
        }
        this.stats.activeNeurons = this.allNeurons.filter(n => n.activity > 0.1).length;
    }

    stimulateRegion(regionId, strength = 1) {
        if (this.regions[regionId]) {
            this.regions[regionId].stimulate(strength);
        } else if (regionId === 'hub') {
            const shuffled = Utils.shuffle([...this.hub.neurons]);
            shuffled.slice(0, 5).forEach(n => n.stimulate(strength));
        }
    }

    handleResize() {
        for (const region of Object.values(this.regions)) {
            region.recalculate();
        }
        this.hub.recalculate();
    }

    injectInput(data) {
        if (this.regions.sensory) {
            for (let i = 0; i < Math.min(data.length, 10); i++) {
                const strength = typeof data[i] === 'number' ? data[i] : 1;
                if (this.regions.sensory.neurons[i]) {
                    this.regions.sensory.neurons[i].stimulate(strength);
                }
            }
        }
    }
}
