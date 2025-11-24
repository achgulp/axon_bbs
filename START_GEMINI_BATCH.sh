#!/bin/bash
# Warzone Lite - Launch Multiple Gemini Tasks in Parallel
# This script launches a batch of tasks simultaneously
# Run from /path/to/axon_bbs/ directory

# Usage: ./START_GEMINI_BATCH.sh <batch_name> <task1> <model1> <task2> <model2> ...
# Example: ./START_GEMINI_BATCH.sh week1_batch1 1.1 flash 1.2 flash 1.3 flash

BATCH_NAME="${1:-batch}"
shift

if [ $# -lt 2 ]; then
    echo "Usage: ./START_GEMINI_BATCH.sh <batch_name> <task1> <model1> [task2] [model2] ..."
    echo "Example: ./START_GEMINI_BATCH.sh week1_batch1 1.1 flash 1.2 flash 1.3 flash"
    exit 1
fi

BATCH_DIR="/tmp/gemini_batch_${BATCH_NAME}"
mkdir -p "$BATCH_DIR"

PIDS_FILE="$BATCH_DIR/pids.txt"
TASKS_FILE="$BATCH_DIR/tasks.txt"
> "$PIDS_FILE"
> "$TASKS_FILE"

echo "═══════════════════════════════════════════════════"
echo "  Starting Gemini Batch: $BATCH_NAME"
echo "═══════════════════════════════════════════════════"
echo ""

TASK_COUNT=0

# Launch all tasks
while [ $# -ge 2 ]; do
    TASK="$1"
    MODEL="$2"
    shift 2

    TASK_COUNT=$((TASK_COUNT + 1))

    if [ "$MODEL" = "pro" ]; then
        MODEL_NAME="gemini-2.5-pro"
        MODEL_LABEL="PRO"
    else
        MODEL_NAME="gemini-2.5-flash"
        MODEL_LABEL="FLASH"
    fi

    OUTPUT_FILE="$BATCH_DIR/task_${TASK}_output.txt"

    echo "[$TASK_COUNT] Launching Task $TASK with $MODEL_LABEL..."

    # Launch in background
    {
        echo "Gemini $MODEL_LABEL started at $(date)"
        echo "Task: $TASK"
        echo "Batch: $BATCH_NAME"
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

    } >> "$OUTPUT_FILE" 2>&1 &

    GEMINI_PID=$!
    echo "$GEMINI_PID" >> "$PIDS_FILE"
    echo "Task $TASK ($MODEL_LABEL): PID $GEMINI_PID → $OUTPUT_FILE" >> "$TASKS_FILE"
    echo "   PID: $GEMINI_PID → $OUTPUT_FILE"
done

echo ""
echo "═══════════════════════════════════════════════════"
echo "✅ Launched $TASK_COUNT tasks in parallel!"
echo ""
echo "Batch directory: $BATCH_DIR"
echo ""
echo "Monitor all tasks:"
echo "   watch -n 1 'ls -lh $BATCH_DIR/*.txt'"
echo ""
echo "Check which are still running:"
echo "   cat $PIDS_FILE | xargs ps -p"
echo ""
echo "View specific task output:"
cat "$TASKS_FILE"
echo ""
echo "When ALL tasks finish, notify Claude Code:"
echo "   'Batch $BATCH_NAME complete. Review $BATCH_DIR'"
echo ""
echo "═══════════════════════════════════════════════════"
