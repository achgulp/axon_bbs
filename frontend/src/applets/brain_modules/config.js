/**
 * Configuration - Central place for all tunable parameters
 * Easy to modify without touching logic code
 */

const CONFIG = {
    // Canvas settings
    canvas: {
        backgroundColor: '#0a0a0f',
        brainPadding: 60  // Padding from edges
    },

    // Brain regions - positions are relative (0-1) within brain bounds
    // Adjusted for new realistic sagittal brain shape
    regions: {
        frontal: {
            name: 'Frontal',
            color: '#00ffff',
            relativePosition: { x: 0.78, y: 0.28 },
            relativeSize: 0.14
        },
        parietal: {
            name: 'Parietal',
            color: '#4488ff',
            relativePosition: { x: 0.42, y: 0.18 },
            relativeSize: 0.13
        },
        temporal: {
            name: 'Temporal',
            color: '#00ff88',
            relativePosition: { x: 0.68, y: 0.55 },
            relativeSize: 0.12
        },
        occipital: {
            name: 'Occipital',
            color: '#ff00ff',
            relativePosition: { x: 0.18, y: 0.38 },
            relativeSize: 0.11
        },
        motor: {
            name: 'Motor',
            color: '#ffff00',
            relativePosition: { x: 0.58, y: 0.22 },
            relativeSize: 0.10
        },
        sensory: {
            name: 'Sensory',
            color: '#ff8844',
            relativePosition: { x: 0.48, y: 0.32 },
            relativeSize: 0.10
        }
    },

    // Central hub - positioned in thalamus area
    hub: {
        color: '#ffaa00',
        glowColor: '#ffaa0040',
        relativePosition: { x: 0.52, y: 0.42 },
        relativeSize: 0.07
    },

    // Neuron settings
    neurons: {
        countPerRegion: 35,       // Fewer neurons = cleaner look
        minRadius: 2,
        maxRadius: 3.5,
        baseColor: '#1a4a5a',     // Inactive color
        activeColor: '#00ffff',   // Active glow
        decayRate: 0.04           // Slightly slower decay for smoother fading
    },

    // Connection settings
    connections: {
        intraRegionProbability: 0.15,   // Chance of connection within region
        hubConnectionProbability: 0.3,  // Chance of connecting to hub
        interRegionProbability: 0.05,   // Chance of cross-region connection
        baseColor: '#1a2a3a',
        activeColor: '#00ffff',
        lineWidth: 0.5,
        activeLineWidth: 2
    },

    // Signal settings
    signals: {
        speed: 0.012,             // Slower so you can see signals travel
        glowRadius: 8,
        color: '#ff00ff',
        trailLength: 5
    },

    // Animation
    animation: {
        fps: 60,
        defaultSpeed: 1.0
    },

    // Dashboard
    dashboard: {
        graphHistoryLength: 100,  // Number of data points in flow graph
        heatmapUpdateInterval: 10 // Frames between heatmap updates
    },

    // Learning settings (Oja's rule online learning)
    learning: {
        enabled: true,              // Learning on by default
        learningRate: 0.02,         // Oja's rule learning rate
        decayRate: 0.01,            // Weight decay rate toward baseline
        minLearningRate: 0.001,
        maxLearningRate: 0.1,
        minDecayRate: 0.001,
        maxDecayRate: 0.05,
        autoTrainInterval: 500,     // ms between auto-train inputs
        settleTicks: 30,            // Ticks to wait before evaluating output
        historyWindow: 20,          // Rolling window for accuracy calculation
        showWeights: false          // Toggle weight visualization on canvas
    }
};

// Freeze to prevent accidental modification
Object.freeze(CONFIG);
