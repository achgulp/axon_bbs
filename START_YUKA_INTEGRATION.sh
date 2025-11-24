#!/bin/bash
# Gemini Agent: Yuka.js Integration Task
# Integrates Yuka.js AI library for professional unit movement

MODEL="${1:-flash}"

if [ "$MODEL" = "pro" ]; then
    MODEL_NAME="gemini-2.5-pro"
    MODEL_LABEL="PRO"
else
    MODEL_NAME="gemini-2.5-flash"
    MODEL_LABEL="FLASH"
fi

# Safe sandbox directory
SANDBOX_DIR="/tmp/gemini_sandbox_yuka_integration"
rm -rf "$SANDBOX_DIR"
mkdir -p "$SANDBOX_DIR"

OUTPUT_FILE="/tmp/gemini_yuka_integration_output.txt"
PID_FILE="/tmp/gemini_yuka_integration.pid"

echo "═══════════════════════════════════════════════════"
echo "  Gemini $MODEL_LABEL: Yuka.js Integration Task"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Sandbox directory: $SANDBOX_DIR"
echo "Output log: $OUTPUT_FILE"
echo ""
echo "Setting up sandbox..."

# Copy task specification
cp /path/to/axon_bbs/TASK_YUKA_INTEGRATION.md "$SANDBOX_DIR/"
echo "  ✓ Copied TASK_YUKA_INTEGRATION.md to sandbox"

# Copy current Warzone_Lite.js
cp /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js "$SANDBOX_DIR/"
echo "  ✓ Copied Warzone_Lite.js to sandbox"

# Copy package.json to verify Yuka is installed
cp /path/to/axon_bbs/frontend/package.json "$SANDBOX_DIR/"
echo "  ✓ Copied package.json to sandbox"

echo ""
echo "Gemini will integrate Yuka.js AI library..."
echo ""

# Start Gemini in background
{
    echo "Gemini $MODEL_LABEL started at $(date)"
    echo "Task: Yuka.js Integration"
    echo "Sandbox: $SANDBOX_DIR"
    echo "═══════════════════════════════════════════════════"
    echo ""

    cd "$SANDBOX_DIR"

    gemini -m "$MODEL_NAME" --yolo -p "You are a skilled JavaScript developer integrating Yuka.js AI library into an RTS game.

TASK: Integrate Yuka.js for Professional Unit Movement

Read TASK_YUKA_INTEGRATION.md for complete specifications.

CURRENT STATE:
- Yuka.js is installed (check package.json dependencies)
- Current code is in Warzone_Lite.js (1903 lines, v3.0.2)
- Units currently use custom A* pathfinding (~lines 1610-1673)
- Movement is functional but not polished (no arrival behavior, no avoidance)

YOUR GOAL:
1. Read TASK_YUKA_INTEGRATION.md completely
2. Read Warzone_Lite.js to understand current structure
3. Follow the step-by-step implementation plan in the task doc
4. Integrate Yuka.js EntityManager and Vehicle agents
5. Replace movement commands with Yuka steering behaviors (Arrive, ObstacleAvoidance)
6. Update animation loop to sync Yuka positions with Three.js meshes
7. Preserve ALL existing systems (combat, selection, altitude, terrain)

CRITICAL REQUIREMENTS:
- DO NOT break existing features
- Preserve debug console, asset loading, combat, selection, altitude
- Units must move smoothly with acceleration/deceleration
- Units must avoid each other
- Air units must maintain altitude while moving
- Follow the implementation steps EXACTLY in TASK_YUKA_INTEGRATION.md

DELIVERABLE:
- Modified Warzone_Lite.js with Yuka.js integrated
- All existing features working
- Smooth, natural unit movement
- No syntax errors

Start by reading TASK_YUKA_INTEGRATION.md, then implement step-by-step.

Ready? Begin integration now."

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "Gemini $MODEL_LABEL finished at $(date)"
    echo ""
    echo "Files in sandbox:"
    ls -lh "$SANDBOX_DIR"
    echo ""
    echo "Modified file size:"
    wc -l "$SANDBOX_DIR/Warzone_Lite.js" 2>/dev/null || echo "No Warzone_Lite.js found"

} >> "$OUTPUT_FILE" 2>&1 &

GEMINI_PID=$!
echo $GEMINI_PID > "$PID_FILE"

echo "✅ Gemini $MODEL_LABEL agent launched!"
echo "   PID: $GEMINI_PID"
echo ""
echo "Monitor progress:"
echo "   tail -f $OUTPUT_FILE"
echo ""
echo "Check sandbox contents:"
echo "   ls -lh $SANDBOX_DIR"
echo ""
echo "Wait for completion:"
echo "   ./WAIT_FOR_GEMINI_BATCH.sh yuka_integration"
echo ""
echo "When done, I'll review and deploy if approved!"
echo ""
echo "═══════════════════════════════════════════════════"
