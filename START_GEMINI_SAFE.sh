#!/bin/bash
# Safe Gemini Workflow - Writes to temp directory first
# Claude Code reviews and approves before moving to production
# Usage: ./START_GEMINI_SAFE.sh <task> <model>

TASK="${1:-0}"
MODEL="${2:-flash}"

if [ "$MODEL" = "pro" ]; then
    MODEL_NAME="gemini-2.5-pro"
    MODEL_LABEL="PRO"
else
    MODEL_NAME="gemini-2.5-flash"
    MODEL_LABEL="FLASH"
fi

# Safe sandbox directory
SANDBOX_DIR="/tmp/gemini_sandbox_task_${TASK}"
rm -rf "$SANDBOX_DIR"
mkdir -p "$SANDBOX_DIR"

OUTPUT_FILE="/tmp/gemini_task_${TASK}_output.txt"
PID_FILE="/tmp/gemini_task_${TASK}.pid"

echo "═══════════════════════════════════════════════════"
echo "  Starting Gemini $MODEL_LABEL on Task $TASK (SAFE MODE)"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Sandbox directory: $SANDBOX_DIR"
echo "Output log: $OUTPUT_FILE"
echo ""
echo "Setting up sandbox..."

# Copy documentation into sandbox
cp -r /path/to/axon_bbs/docs "$SANDBOX_DIR/"
echo "  ✓ Copied docs/ to sandbox"

# Copy existing code files that might be modified
if [ -f /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js ]; then
    cp /path/to/axon_bbs/frontend/src/applets/Warzone_Lite.js "$SANDBOX_DIR/"
    echo "  ✓ Copied Warzone_Lite.js to sandbox"
fi

if [ -f /path/to/axon_bbs/frontend/src/applets/Test_BBS_API.js ]; then
    cp /path/to/axon_bbs/frontend/src/applets/Test_BBS_API.js "$SANDBOX_DIR/"
    echo "  ✓ Copied Test_BBS_API.js to sandbox"
fi

echo ""
echo "Gemini will work in isolated sandbox."
echo "Claude Code will review, then move to production."
echo ""

# Start Gemini in background
{
    echo "Gemini $MODEL_LABEL started at $(date)"
    echo "Task: $TASK"
    echo "Sandbox: $SANDBOX_DIR"
    echo "═══════════════════════════════════════════════════"
    echo ""

    cd "$SANDBOX_DIR"

    gemini -m "$MODEL_NAME" --yolo -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md You are a junior developer on the Warzone Lite project working in a safe sandbox.

TASK: Complete Task $TASK from JUNIOR_DEV_TASKS.md

SANDBOX SETUP:
- All documentation is in ./docs/ (already copied for you)
- Existing code files are in current directory (Warzone_Lite.js, Test_BBS_API.js)
- You are working in: $SANDBOX_DIR
- All your changes stay in this sandbox until approved

INSTRUCTIONS:
1. Read docs/JUNIOR_DEV_ONBOARDING.md completely
2. Read Task $TASK section in docs/JUNIOR_DEV_TASKS.md
3. If task modifies existing file (like Warzone_Lite.js), read it from current directory
4. Follow the template EXACTLY as shown in the task
5. Write modified/new files to current directory
6. Copy templates exactly - no improvisation!

When complete, confirm which files you created/modified.

Ready? Complete Task $TASK now."

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "Gemini $MODEL_LABEL finished at $(date)"
    echo ""
    echo "Files created in sandbox:"
    ls -lh "$SANDBOX_DIR"

} >> "$OUTPUT_FILE" 2>&1 &

GEMINI_PID=$!
echo $GEMINI_PID > "$PID_FILE"

echo "✅ Gemini $MODEL_LABEL started in SAFE MODE!"
echo "   PID: $GEMINI_PID"
echo ""
echo "Monitor progress:"
echo "   tail -f $OUTPUT_FILE"
echo ""
echo "Check sandbox contents:"
echo "   ls -lh $SANDBOX_DIR"
echo ""
echo "When done, notify Claude Code:"
echo "   'Task $TASK finished in sandbox'"
echo ""
echo "Claude Code will:"
echo "  1. Review files in $SANDBOX_DIR"
echo "  2. Approve or request changes"
echo "  3. Move approved files to production"
echo ""
echo "═══════════════════════════════════════════════════"
