#!/bin/bash
# Warzone Lite - Start Gemini in Background
# This script runs Gemini as a background job
# Run from /path/to/axon_bbs/ directory

# Usage: ./START_GEMINI_BACKGROUND.sh <task_number> [flash|pro]
# Example: ./START_GEMINI_BACKGROUND.sh 0 flash
# Example: ./START_GEMINI_BACKGROUND.sh 1.1 pro

TASK="${1:-0}"
MODEL="${2:-flash}"

if [ "$MODEL" = "pro" ]; then
    MODEL_NAME="gemini-2.5-pro"
    MODEL_LABEL="PRO"
else
    MODEL_NAME="gemini-2.5-flash"
    MODEL_LABEL="FLASH"
fi

OUTPUT_FILE="/tmp/gemini_task_${TASK}_output.txt"
PID_FILE="/tmp/gemini_task_${TASK}.pid"

echo "═══════════════════════════════════════════════════"
echo "  Starting Gemini $MODEL_LABEL on Task $TASK (Background)"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Output will be saved to: $OUTPUT_FILE"
echo ""

# Clear previous output
> "$OUTPUT_FILE"

# Start Gemini in background
{
    echo "Gemini $MODEL_LABEL started at $(date)"
    echo "Task: $TASK"
    echo "═══════════════════════════════════════════════════"
    echo ""

    gemini -m "$MODEL_NAME" --yolo -p "@docs/JUNIOR_DEV_ONBOARDING.md @docs/JUNIOR_DEV_TASKS.md You are a junior developer on the Warzone Lite project.

TASK: Complete Task $TASK from JUNIOR_DEV_TASKS.md

INSTRUCTIONS:
1. Read JUNIOR_DEV_ONBOARDING.md completely to understand Axon BBS
2. Read Task $TASK section in JUNIOR_DEV_TASKS.md
3. Follow the template EXACTLY - copy it precisely as shown
4. CREATE or MODIFY the file as specified in the task
5. Use the EXACT file paths specified in the task documentation
6. Do NOT modify the templates - copy them exactly

IMPORTANT:
- Use your file writing tools to create/modify files directly
- Follow the exact file paths from the task documentation
- Copy templates exactly as shown in JUNIOR_DEV_TASKS.md

When complete, confirm the file was created successfully.

Ready? Complete Task $TASK now."

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo "Gemini $MODEL_LABEL finished at $(date)"
    echo "Task $TASK complete!"

} >> "$OUTPUT_FILE" 2>&1 &

GEMINI_PID=$!
echo $GEMINI_PID > "$PID_FILE"

echo "✅ Gemini $MODEL_LABEL started in background!"
echo "   PID: $GEMINI_PID"
echo ""
echo "Monitor progress with:"
echo "   tail -f $OUTPUT_FILE"
echo ""
echo "Check if still running:"
echo "   ps -p $GEMINI_PID"
echo ""
echo "Or just check the output file size:"
echo "   ls -lh $OUTPUT_FILE"
echo ""
echo "When done, notify Claude Code:"
echo "   'Gemini finished Task $TASK. Review $OUTPUT_FILE'"
echo ""
echo "═══════════════════════════════════════════════════"
