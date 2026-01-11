/**
 * Network Renderer - MINIMAL BEAUTY Edition
 *
 * Philosophy: Less is more
 * - NO connection lines drawn at all
 * - Neurons glow like stars/fireflies
 * - Activity flows visually through sequential neuron activation
 * - Regions have ambient glow based on activity
 * - Clean, elegant, performant
 */

class NetworkRenderer {
    constructor(ctx, network) {
        this.ctx = ctx;
        this.network = network;
        this.time = 0;
        this.showWeights = false;  // Toggle for weight visualization
    }

    render() {
        this.time += 0.02;

        // Layer 0: Learned weights (if enabled)
        if (this.showWeights) {
            this.renderLearnedWeights();
        }

        // Layer 1: Region ambient glow (shows overall activity areas)
        this.renderRegionGlow();

        // Layer 2: Active signal paths (subtle, only when signals traveling)
        this.renderActiveSignals();

        // Layer 3: Neurons (the stars)
        this.renderNeurons();

        // Layer 4: Hub
        this.renderHub();

        // Layer 5: Labels (subtle)
        this.renderRegionLabels();

        // Layer 6: Learning events (sparkles for weight changes)
        if (this.showWeights) {
            this.renderLearningEvents();
        }
    }

    /**
     * Render signal paths - OPTIMIZED
     * - No gradients (expensive)
     * - Batched rendering
     * - Fading trails using connection.activity
     * - Region-colored signals
     */
    renderActiveSignals() {
        const ctx = this.ctx;

        // Collect fading trails and active signals separately
        const fadingTrails = [];
        const activeSignals = [];

        for (const conn of this.network.connections) {
            if (conn.activity > 0.03) {
                fadingTrails.push(conn);
            }
            if (conn.pulseActive) {
                activeSignals.push(conn);
            }
        }

        // Render fading trails with region colors
        if (fadingTrails.length > 0) {
            ctx.lineCap = 'round';
            ctx.lineWidth = 1;

            for (const conn of fadingTrails) {
                const alpha = conn.activity * 0.15;
                const regionId = conn.from.regionId;
                const color = this.getRegionColor(regionId);

                ctx.beginPath();
                ctx.moveTo(conn.from.x, conn.from.y);
                ctx.lineTo(conn.to.x, conn.to.y);
                ctx.strokeStyle = Utils.hexToRgba(color, alpha);
                ctx.stroke();
            }
        }

        // Render signal dots with region colors
        if (activeSignals.length > 0) {
            for (const conn of activeSignals) {
                const t = conn.pulsePhase;
                const sx = conn.from.x + (conn.to.x - conn.from.x) * t;
                const sy = conn.from.y + (conn.to.y - conn.from.y) * t;

                const regionId = conn.from.regionId;
                const color = this.getRegionColor(regionId);

                // Subtle glow
                ctx.fillStyle = Utils.hexToRgba(color, 0.5);
                ctx.beginPath();
                ctx.arc(sx, sy, 3, 0, Math.PI * 2);
                ctx.fill();

                // Bright core
                ctx.fillStyle = Utils.hexToRgba(color, 0.9);
                ctx.beginPath();
                ctx.arc(sx, sy, 1.2, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }

    /**
     * Get color for a region (or hub)
     */
    getRegionColor(regionId) {
        if (regionId === 'hub') {
            return CONFIG.hub.color;
        }
        const region = this.network.regions[regionId];
        return region ? region.config.color : '#00ffff';
    }

    /**
     * Render soft ambient glow for each region based on activity
     * This shows "areas" of the brain lighting up
     */
    renderRegionGlow() {
        const ctx = this.ctx;

        for (const region of Object.values(this.network.regions)) {
            const activity = region.totalActivity;
            if (activity < 0.05) continue;

            // Soft region glow
            const glowRadius = region.radius * (1.2 + activity * 0.5);
            const gradient = ctx.createRadialGradient(
                region.x, region.y, 0,
                region.x, region.y, glowRadius
            );

            const color = region.config.color;
            gradient.addColorStop(0, Utils.hexToRgba(color, activity * 0.15));
            gradient.addColorStop(0.5, Utils.hexToRgba(color, activity * 0.05));
            gradient.addColorStop(1, 'transparent');

            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(region.x, region.y, glowRadius, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    /**
     * Render neurons - the heart of the visualization
     * Each neuron is a glowing point of light
     */
    renderNeurons() {
        const ctx = this.ctx;

        for (const region of Object.values(this.network.regions)) {
            const color = region.config.color;

            for (const neuron of region.neurons) {
                this.renderNeuron(neuron, color);
            }
        }
    }

    /**
     * Render a single neuron based on its state
     */
    renderNeuron(neuron, color) {
        const ctx = this.ctx;
        const activity = neuron.activity;

        if (neuron.justFired) {
            // FIRING: Bright flash - the "spark"
            this.renderNeuronFlash(neuron, color);
        } else if (activity > 0.15) {
            // ACTIVE: Glowing ember
            this.renderNeuronGlow(neuron, color, activity);
        } else {
            // IDLE: Tiny dim dot
            this.renderNeuronIdle(neuron, color);
        }
    }

    /**
     * Neuron just fired - bright flash
     */
    renderNeuronFlash(neuron, color) {
        const ctx = this.ctx;
        const size = neuron.radius * 5;

        // Outer glow burst
        const gradient = ctx.createRadialGradient(
            neuron.x, neuron.y, 0,
            neuron.x, neuron.y, size
        );
        gradient.addColorStop(0, '#ffffff');
        gradient.addColorStop(0.15, Utils.hexToRgba(color, 0.9));
        gradient.addColorStop(0.4, Utils.hexToRgba(color, 0.3));
        gradient.addColorStop(1, 'transparent');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(neuron.x, neuron.y, size, 0, Math.PI * 2);
        ctx.fill();
    }

    /**
     * Active neuron - soft glow
     */
    renderNeuronGlow(neuron, color, intensity) {
        const ctx = this.ctx;
        const size = neuron.radius * (1.5 + intensity * 2);

        // Glow
        const gradient = ctx.createRadialGradient(
            neuron.x, neuron.y, 0,
            neuron.x, neuron.y, size
        );
        gradient.addColorStop(0, Utils.hexToRgba(color, 0.7 + intensity * 0.3));
        gradient.addColorStop(0.3, Utils.hexToRgba(color, intensity * 0.5));
        gradient.addColorStop(1, 'transparent');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(neuron.x, neuron.y, size, 0, Math.PI * 2);
        ctx.fill();

        // Bright core
        if (intensity > 0.4) {
            ctx.fillStyle = `rgba(255,255,255,${intensity * 0.6})`;
            ctx.beginPath();
            ctx.arc(neuron.x, neuron.y, neuron.radius * 0.5, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    /**
     * Idle neuron - barely visible dot
     */
    renderNeuronIdle(neuron, color) {
        const ctx = this.ctx;

        ctx.fillStyle = Utils.hexToRgba(color, 0.2);
        ctx.beginPath();
        ctx.arc(neuron.x, neuron.y, neuron.radius * 0.6, 0, Math.PI * 2);
        ctx.fill();
    }

    /**
     * Render the central hub
     */
    renderHub() {
        const ctx = this.ctx;
        const hub = this.network.hub;

        // Hub activity
        let hubActivity = 0;
        for (const neuron of hub.neurons) {
            hubActivity += neuron.activity;
        }
        hubActivity = hub.neurons.length > 0 ? hubActivity / hub.neurons.length : 0;

        // Hub ambient glow with subtle pulse
        const pulse = 0.9 + Math.sin(this.time * 1.5) * 0.1;
        const glowSize = hub.radius * 1.3;

        const gradient = ctx.createRadialGradient(
            hub.x, hub.y, 0,
            hub.x, hub.y, glowSize
        );
        gradient.addColorStop(0, Utils.hexToRgba(CONFIG.hub.color, (0.12 + hubActivity * 0.3) * pulse));
        gradient.addColorStop(0.6, Utils.hexToRgba(CONFIG.hub.color, 0.03 * pulse));
        gradient.addColorStop(1, 'transparent');

        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(hub.x, hub.y, glowSize, 0, Math.PI * 2);
        ctx.fill();

        // Hub ring
        ctx.strokeStyle = Utils.hexToRgba(CONFIG.hub.color, 0.25 + hubActivity * 0.35);
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(hub.x, hub.y, hub.radius, 0, Math.PI * 2);
        ctx.stroke();

        // Hub neurons
        for (const neuron of hub.neurons) {
            this.renderNeuron(neuron, CONFIG.hub.color);
        }
    }

    /**
     * Subtle region labels
     */
    renderRegionLabels() {
        const ctx = this.ctx;
        ctx.font = '9px monospace';
        ctx.textAlign = 'center';

        for (const [id, region] of Object.entries(this.network.regions)) {
            const alpha = 0.2 + region.totalActivity * 0.4;
            ctx.fillStyle = Utils.hexToRgba(region.config.color, alpha);
            ctx.fillText(
                region.config.name,
                region.x,
                region.y - region.radius - 8
            );
        }

        ctx.fillStyle = Utils.hexToRgba(CONFIG.hub.color, 0.35);
        ctx.fillText('Hub', this.network.hub.x, this.network.hub.y - this.network.hub.radius - 8);
    }

    /**
     * Render active learning - only shows connections that are CURRENTLY learning
     * Uses lastWeightChange which decays, so only recent activity shows
     */
    renderLearnedWeights() {
        const ctx = this.ctx;
        const threshold = 0.02;  // Minimum recent change to show

        ctx.lineCap = 'round';

        for (const conn of this.network.connections) {
            // Only show connections with RECENT weight changes (not cumulative)
            if (conn.lastWeightChange < threshold) continue;

            const delta = conn.getWeightDelta();
            const intensity = Math.min(1, conn.lastWeightChange * 5);

            // Color based on direction of change
            let color;
            if (delta > 0) {
                color = '#00ff88';  // Strengthening - green
            } else {
                color = '#ff6666';  // Weakening - red
            }

            // Very subtle, fades quickly
            const alpha = intensity * 0.2;
            const thickness = 0.5 + intensity;

            ctx.beginPath();
            ctx.moveTo(conn.from.x, conn.from.y);
            ctx.lineTo(conn.to.x, conn.to.y);
            ctx.strokeStyle = Utils.hexToRgba(color, alpha);
            ctx.lineWidth = thickness;
            ctx.stroke();
        }
    }

    /**
     * Render learning events - sparkle effects when weights change significantly
     */
    renderLearningEvents() {
        const ctx = this.ctx;

        for (const conn of this.network.connections) {
            if (conn.lastWeightChange > 0.08) {
                // Calculate midpoint of connection
                const mx = (conn.from.x + conn.to.x) / 2;
                const my = (conn.from.y + conn.to.y) / 2;

                // Sparkle effect - subtle
                const intensity = Math.min(1, conn.lastWeightChange * 3);
                const size = 1.5 + intensity * 2;

                // Soft glow
                ctx.fillStyle = `rgba(255, 255, 255, ${intensity * 0.3})`;
                ctx.beginPath();
                ctx.arc(mx, my, size, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
}
