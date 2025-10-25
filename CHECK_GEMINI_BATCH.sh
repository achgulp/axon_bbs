#!/bin/bash
# Check status of Gemini batch jobs
# Usage: ./CHECK_GEMINI_BATCH.sh <batch_name>

BATCH_NAME="${1:-batch}"
BATCH_DIR="/tmp/gemini_batch_${BATCH_NAME}"

if [ ! -d "$BATCH_DIR" ]; then
    echo "❌ Batch '$BATCH_NAME' not found!"
    echo "   Directory $BATCH_DIR does not exist"
    exit 1
fi

PIDS_FILE="$BATCH_DIR/pids.txt"
TASKS_FILE="$BATCH_DIR/tasks.txt"

echo "═══════════════════════════════════════════════════"
echo "  Batch Status: $BATCH_NAME"
echo "═══════════════════════════════════════════════════"
echo ""

# Read PIDs
if [ -f "$PIDS_FILE" ]; then
    PIDS=$(cat "$PIDS_FILE")
    TOTAL_TASKS=$(wc -l < "$PIDS_FILE")
    RUNNING_COUNT=0
    FINISHED_COUNT=0

    echo "Tasks:"
    echo ""

    while IFS= read -r line; do
        echo "  $line"
    done < "$TASKS_FILE"

    echo ""
    echo "Status Check:"
    echo ""

    for PID in $PIDS; do
        if ps -p $PID > /dev/null 2>&1; then
            echo "  [RUNNING] PID $PID"
            RUNNING_COUNT=$((RUNNING_COUNT + 1))
        else
            echo "  [DONE]    PID $PID ✓"
            FINISHED_COUNT=$((FINISHED_COUNT + 1))
        fi
    done

    echo ""
    echo "Progress: $FINISHED_COUNT / $TOTAL_TASKS complete"

    if [ $RUNNING_COUNT -eq 0 ]; then
        echo ""
        echo "🎉 ALL TASKS COMPLETE!"
        echo ""
        echo "Output files:"
        ls -lh "$BATCH_DIR"/*.txt
        echo ""
        echo "Next: Notify Claude Code:"
        echo "   'Batch $BATCH_NAME complete. Review $BATCH_DIR'"
    else
        echo ""
        echo "⏳ Still running: $RUNNING_COUNT tasks"
        echo ""
        echo "Estimated time: ~30 seconds total from start"
    fi
else
    echo "❌ No PID file found!"
fi

echo ""
echo "═══════════════════════════════════════════════════"
