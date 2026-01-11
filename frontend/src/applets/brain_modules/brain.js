/**
 * Brain rendering module
 * Handles drawing the brain outline and managing canvas
 */

class BrainRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.bounds = { x: 0, y: 0, width: 0, height: 0 };
        this.brainPath = null;
        this.cerebrumPath = null;
        this.cerebellumPath = null;
        this.brainstemPath = null;

        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width * window.devicePixelRatio;
        this.canvas.height = rect.height * window.devicePixelRatio;
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
        this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

        // Calculate brain bounds (with padding)
        const padding = CONFIG.canvas.brainPadding;
        const availableWidth = rect.width - padding * 2 - 80;
        const availableHeight = rect.height - padding * 2;

        // Brain aspect ratio ~1.1:1
        const brainAspect = 1.15;
        let brainWidth, brainHeight;

        if (availableWidth / availableHeight > brainAspect) {
            brainHeight = availableHeight;
            brainWidth = brainHeight * brainAspect;
        } else {
            brainWidth = availableWidth;
            brainHeight = brainWidth / brainAspect;
        }

        this.bounds = {
            x: padding + 60 + (availableWidth - brainWidth) / 2,
            y: padding + (availableHeight - brainHeight) / 2,
            width: brainWidth,
            height: brainHeight
        };

        this.generateBrainPaths();
    }

    /**
     * Generate realistic brain outline paths (sagittal view)
     * Includes cerebrum, cerebellum, and brainstem
     */
    generateBrainPaths() {
        const { x, y, width, height } = this.bounds;

        // Main cerebrum path - REVERSED (Front is now on the RIGHT)
        this.cerebrumPath = new Path2D();

        // Start at frontal lobe base (right side)
        this.cerebrumPath.moveTo(x + width * 0.88, y + height * 0.60);

        // Frontal lobe - on the right
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.95, y + height * 0.55,
            x + width * 1.00, y + height * 0.48,
            x + width * 0.99, y + height * 0.40
        );
        this.cerebrumPath.bezierCurveTo(
            x + width * 1.00, y + height * 0.32,
            x + width * 0.96, y + height * 0.24,
            x + width * 0.90, y + height * 0.18
        );
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.85, y + height * 0.12,
            x + width * 0.78, y + height * 0.08,
            x + width * 0.70, y + height * 0.05
        );

        // Superior frontal gyrus and motor/sensory peaks
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.65, y + height * 0.03,
            x + width * 0.58, y + height * 0.03,
            x + width * 0.52, y + height * 0.04
        );
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.48, y + height * 0.02,
            x + width * 0.42, y + height * 0.03,
            x + width * 0.35, y + height * 0.06
        );

        // Parietal lobe curve (towards left)
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.28, y + height * 0.09,
            x + width * 0.18, y + height * 0.15,
            x + width * 0.10, y + height * 0.25
        );

        // Occipital lobe - now on the left
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.02, y + height * 0.35,
            x + width * 0.01, y + height * 0.45,
            x + width * 0.05, y + height * 0.55
        );

        // Under-occipital area towards temporal
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.10, y + height * 0.62,
            x + width * 0.20, y + height * 0.65,
            x + width * 0.30, y + height * 0.64
        );

        // Temporal lobe - the "thumb" (pointing right)
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.35, y + height * 0.68,
            x + width * 0.40, y + height * 0.75,
            x + width * 0.50, y + height * 0.78
        );
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.65, y + height * 0.82,
            x + width * 0.82, y + height * 0.78,
            x + width * 0.90, y + height * 0.68
        );

        // Closing back to frontal base
        this.cerebrumPath.bezierCurveTo(
            x + width * 0.92, y + height * 0.65,
            x + width * 0.90, y + height * 0.62,
            x + width * 0.88, y + height * 0.60
        );

        this.cerebrumPath.closePath();

        // Cerebellum (on the right/posterior side)
        this.cerebellumPath = new Path2D();
        this.cerebellumPath.moveTo(x + width * 0.70, y + height * 0.65);
        this.cerebellumPath.bezierCurveTo(
            x + width * 0.75, y + height * 0.68,
            x + width * 0.85, y + height * 0.70,
            x + width * 0.95, y + height * 0.75
        );
        this.cerebellumPath.bezierCurveTo(
            x + width * 1.00, y + height * 0.82,
            x + width * 0.95, y + height * 0.92,
            x + width * 0.85, y + height * 0.96
        );
        this.cerebellumPath.bezierCurveTo(
            x + width * 0.75, y + height * 0.98,
            x + width * 0.65, y + height * 0.95,
            x + width * 0.60, y + height * 0.88
        );
        this.cerebellumPath.bezierCurveTo(
            x + width * 0.58, y + height * 0.80,
            x + width * 0.62, y + height * 0.70,
            x + width * 0.70, y + height * 0.65
        );
        this.cerebellumPath.closePath();

        // Brainstem (on the right/posterior side, behind temporal lobe)
        this.brainstemPath = new Path2D();
        this.brainstemPath.moveTo(x + width * 0.58, y + height * 0.70);
        // Pons bulge (pointing right/posterior)
        this.brainstemPath.bezierCurveTo(
            x + width * 0.60, y + height * 0.75,
            x + width * 0.60, y + height * 0.85,
            x + width * 0.58, y + height * 0.90
        );
        // Medulla taper
        this.brainstemPath.lineTo(x + width * 0.55, y + height * 1.00);
        this.brainstemPath.lineTo(x + width * 0.50, y + height * 1.00);
        this.brainstemPath.lineTo(x + width * 0.48, y + height * 0.90);
        this.brainstemPath.bezierCurveTo(
            x + width * 0.46, y + height * 0.85,
            x + width * 0.46, y + height * 0.75,
            x + width * 0.48, y + height * 0.70
        );
        this.brainstemPath.closePath();

        // Combined brain path for hit testing
        this.brainPath = new Path2D();
        this.brainPath.addPath(this.cerebrumPath);
        this.brainPath.addPath(this.cerebellumPath);
        this.brainPath.addPath(this.brainstemPath);
    }

    /**
     * Check if a point is inside the brain
     */
    isPointInBrain(x, y) {
        return this.ctx.isPointInPath(this.cerebrumPath, x, y) ||
               this.ctx.isPointInPath(this.cerebellumPath, x, y);
    }

    /**
     * Get absolute position from relative brain coordinates
     */
    getAbsolutePosition(relX, relY) {
        return {
            x: this.bounds.x + this.bounds.width * relX,
            y: this.bounds.y + this.bounds.height * relY
        };
    }

    /**
     * Draw the brain outline
     */
    drawBrainOutline() {
        const ctx = this.ctx;

        // Outer glow for cerebrum
        ctx.save();
        ctx.shadowColor = '#4a2a6a';
        ctx.shadowBlur = 25;
        ctx.strokeStyle = '#2a1a3a';
        ctx.lineWidth = 12;
        ctx.stroke(this.cerebrumPath);
        ctx.restore();

        // Cerebrum fill
        const cerebrumGradient = ctx.createRadialGradient(
            this.bounds.x + this.bounds.width * 0.35,
            this.bounds.y + this.bounds.height * 0.3,
            0,
            this.bounds.x + this.bounds.width * 0.5,
            this.bounds.y + this.bounds.height * 0.4,
            this.bounds.width * 0.5
        );
        cerebrumGradient.addColorStop(0, '#1c1828');
        cerebrumGradient.addColorStop(0.5, '#151320');
        cerebrumGradient.addColorStop(1, '#0f0d18');

        ctx.fillStyle = cerebrumGradient;
        ctx.fill(this.cerebrumPath);

        // Cerebrum outline
        ctx.strokeStyle = '#3d2d52';
        ctx.lineWidth = 2;
        ctx.stroke(this.cerebrumPath);

        // Cerebellum (slightly different shade)
        ctx.save();
        ctx.shadowColor = '#3a2050';
        ctx.shadowBlur = 15;
        ctx.fillStyle = '#14111c';
        ctx.fill(this.cerebellumPath);
        ctx.restore();

        ctx.strokeStyle = '#352845';
        ctx.lineWidth = 1.5;
        ctx.stroke(this.cerebellumPath);

        // Brainstem
        ctx.fillStyle = '#12101a';
        ctx.fill(this.brainstemPath);
        ctx.strokeStyle = '#2d2540';
        ctx.lineWidth = 1.5;
        ctx.stroke(this.brainstemPath);

        // Draw sulci and gyri details
        this.drawSulci();
        this.drawCerebellumFolds();
    }

    /**
     * Draw brain folds (sulci) for realistic look
     */
    drawSulci() {
        const ctx = this.ctx;
        const { x, y, width, height } = this.bounds;

        ctx.strokeStyle = '#2a1d3d';
        ctx.lineWidth = 1.8;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // Central sulcus (Rolandic fissure) - REVERSED
        ctx.globalAlpha = 0.7;
        ctx.beginPath();
        ctx.moveTo(x + width * 0.50, y + height * 0.04);
        ctx.bezierCurveTo(
            x + width * 0.51, y + height * 0.15,
            x + width * 0.53, y + height * 0.25,
            x + width * 0.56, y + height * 0.42
        );
        ctx.stroke();

        // Branch from central sulcus (Pre-central branch) - REVERSED
        ctx.beginPath();
        ctx.moveTo(x + width * 0.53, y + height * 0.20);
        ctx.bezierCurveTo(x + width * 0.58, y + height * 0.22, x + width * 0.62, y + height * 0.28, x + width * 0.64, y + height * 0.35);
        ctx.stroke();

        // Lateral sulcus (Sylvian fissure) - REVERSED
        ctx.lineWidth = 2.4;
        ctx.beginPath();
        ctx.moveTo(x + width * 0.88, y + height * 0.58);
        ctx.bezierCurveTo(
            x + width * 0.75, y + height * 0.55,
            x + width * 0.55, y + height * 0.58,
            x + width * 0.35, y + height * 0.62
        );
        ctx.stroke();

        // Branch from lateral sulcus up (Ascending branch) - REVERSED
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.moveTo(x + width * 0.70, y + height * 0.56);
        ctx.lineTo(x + width * 0.72, y + height * 0.45);
        ctx.stroke();

        // Parieto-occipital sulcus - REVERSED
        ctx.beginPath();
        ctx.moveTo(x + width * 0.25, y + height * 0.10);
        ctx.bezierCurveTo(
            x + width * 0.26, y + height * 0.25,
            x + width * 0.28, y + height * 0.35,
            x + width * 0.26, y + height * 0.55
        );
        ctx.stroke();

        // Precentral sulcus - REVERSED
        ctx.globalAlpha = 0.5;
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(x + width * 0.62, y + height * 0.08);
        ctx.bezierCurveTo(
            x + width * 0.64, y + height * 0.20,
            x + width * 0.68, y + height * 0.30,
            x + width * 0.70, y + height * 0.45
        );
        ctx.stroke();

        // Superior frontal sulcus - REVERSED
        ctx.beginPath();
        ctx.moveTo(x + width * 0.75, y + height * 0.15);
        ctx.bezierCurveTo(
            x + width * 0.80, y + height * 0.25,
            x + width * 0.85, y + height * 0.35,
            x + width * 0.88, y + height * 0.48
        );
        ctx.stroke();

        // Intraparietal sulcus - REVERSED
        ctx.beginPath();
        ctx.moveTo(x + width * 0.40, y + height * 0.12);
        ctx.bezierCurveTo(
            x + width * 0.35, y + height * 0.25,
            x + width * 0.28, y + height * 0.35,
            x + width * 0.25, y + height * 0.48
        );
        ctx.stroke();

        // Superior temporal sulcus - REVERSED
        ctx.beginPath();
        ctx.moveTo(x + width * 0.82, y + height * 0.68);
        ctx.bezierCurveTo(
            x + width * 0.65, y + height * 0.72,
            x + width * 0.48, y + height * 0.75,
            x + width * 0.38, y + height * 0.70
        );
        ctx.stroke();

        // Inferior temporal sulcus - REVERSED
        ctx.beginPath();
        ctx.moveTo(x + width * 0.75, y + height * 0.78);
        ctx.bezierCurveTo(
            x + width * 0.60, y + height * 0.82,
            x + width * 0.45, y + height * 0.80,
            x + width * 0.40, y + height * 0.75
        );
        ctx.stroke();

        // Calcarine sulcus (deep in occipital) - REVERSED
        ctx.beginPath();
        ctx.moveTo(x + width * 0.12, y + height * 0.48);
        ctx.bezierCurveTo(
            x + width * 0.18, y + height * 0.52,
            x + width * 0.25, y + height * 0.54,
            x + width * 0.32, y + height * 0.52
        );
        ctx.stroke();

        // Additional gyri details for "texture" - REVERSED
        ctx.globalAlpha = 0.3;
        const drawTexture = (sx, sy, cp1x, cp1y, ex, ey) => {
            ctx.beginPath();
            ctx.moveTo(x + width * (1-sx), y + height * sy);
            ctx.quadraticCurveTo(x + width * (1-cp1x), y + height * cp1y, x + width * (1-ex), y + height * ey);
            ctx.stroke();
        };

        drawTexture(0.20, 0.30, 0.22, 0.25, 0.25, 0.28);
        drawTexture(0.45, 0.15, 0.48, 0.12, 0.52, 0.14);
        drawTexture(0.70, 0.25, 0.75, 0.22, 0.80, 0.26);
        drawTexture(0.15, 0.45, 0.18, 0.42, 0.22, 0.44);
        drawTexture(0.85, 0.35, 0.88, 0.32, 0.92, 0.36);
        drawTexture(0.55, 0.65, 0.58, 0.68, 0.62, 0.66);

        ctx.globalAlpha = 1;
    }

    /**
     * Draw cerebellum folia (folds) - more intricate
     */
    drawCerebellumFolds() {
        const ctx = this.ctx;
        const { x, y, width, height } = this.bounds;

        ctx.strokeStyle = '#2a1d3d';
        ctx.lineWidth = 1.0;
        ctx.globalAlpha = 0.4;

        // Radiating folia lines (on the right/posterior side)
        const center = { x: x + width * 0.65, y: y + height * 0.75 };
        for (let i = 0; i < 8; i++) {
            const angle = 0.5 + i * 0.15;
            
            ctx.beginPath();
            ctx.moveTo(center.x, center.y);
            const targetX = center.x + Math.cos(angle) * width * 0.2;
            const targetY = center.y + Math.sin(angle) * height * 0.2;
            ctx.bezierCurveTo(
                center.x + width * 0.05, center.y + height * 0.05,
                targetX - width * 0.05, targetY - height * 0.05,
                targetX, targetY
            );
            ctx.stroke();

            // Tiny branches
            ctx.beginPath();
            ctx.moveTo(center.x + (targetX - center.x) * 0.6, center.y + (targetY - center.y) * 0.6);
            ctx.lineTo(center.x + (targetX - center.x) * 0.6 + width * 0.02, center.y + (targetY - center.y) * 0.6 - height * 0.02);
            ctx.stroke();
        }

        // Concentric layering lines
        ctx.globalAlpha = 0.2;
        for (let i = 0; i < 4; i++) {
            const radius = 0.05 + i * 0.04;
            ctx.beginPath();
            ctx.arc(center.x, center.y, width * radius, 0, Math.PI * 2);
            ctx.stroke();
        }

        ctx.globalAlpha = 1;
    }

    /**
     * Clear the canvas
     */
    clear() {
        const ctx = this.ctx;
        ctx.fillStyle = CONFIG.canvas.backgroundColor;
        ctx.fillRect(0, 0, this.canvas.width / window.devicePixelRatio,
                     this.canvas.height / window.devicePixelRatio);
    }

    /**
     * Main render call
     */
    render() {
        this.clear();
        this.drawBrainOutline();
    }
}
