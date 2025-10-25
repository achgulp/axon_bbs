#!/bin/bash
# Wait for Gemini batch to complete, then notify
# This script polls until all tasks finish, then displays ready message
# Usage: ./WAIT_FOR_GEMINI_BATCH.sh <batch_name>

BATCH_NAME="${1:-batch}"
BATCH_DIR="/tmp/gemini_batch_${BATCH_NAME}"

if [ ! -d "$BATCH_DIR" ]; then
    echo "❌ Batch '$BATCH_NAME' not found!"
    echo "   Directory $BATCH_DIR does not exist"
    exit 1
fi

PIDS_FILE="$BATCH_DIR/pids.txt"
TASKS_FILE="$BATCH_DIR/tasks.txt"

if [ ! -f "$PIDS_FILE" ]; then
    echo "❌ No PID file found!"
    exit 1
fi

TOTAL_TASKS=$(wc -l < "$PIDS_FILE")
START_TIME=$(date +%s)

echo "═══════════════════════════════════════════════════"
echo "  Waiting for Batch: $BATCH_NAME"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Total tasks: $TOTAL_TASKS"
echo "Started monitoring at: $(date)"
echo ""

# Poll every 2 seconds
while true; do
    RUNNING_COUNT=0
    FINISHED_COUNT=0

    while IFS= read -r PID; do
        if ps -p $PID > /dev/null 2>&1; then
            RUNNING_COUNT=$((RUNNING_COUNT + 1))
        else
            FINISHED_COUNT=$((FINISHED_COUNT + 1))
        fi
    done < "$PIDS_FILE"

    # Clear line and show progress
    printf "\r⏳ Progress: $FINISHED_COUNT / $TOTAL_TASKS complete"

    # All done?
    if [ $RUNNING_COUNT -eq 0 ]; then
        break
    fi

    sleep 2
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo ""
echo "═══════════════════════════════════════════════════"
echo "🎉 BATCH COMPLETE!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "Batch: $BATCH_NAME"
echo "Tasks: $TOTAL_TASKS"
echo "Duration: ${DURATION} seconds"
echo "Finished at: $(date)"
echo ""
echo "Output files:"
echo ""
ls -lh "$BATCH_DIR"/*.txt 2>/dev/null | while read line; do
    echo "  $line"
done
echo ""
echo "Task details:"
cat "$TASKS_FILE"
echo ""
echo "═══════════════════════════════════════════════════"
echo ""
echo "✅ READY FOR REVIEW"
echo ""
echo "Copy this message to Claude Code:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Batch $BATCH_NAME complete. Review $BATCH_DIR"
echo ""
echo "All $TOTAL_TASKS tasks finished in ${DURATION} seconds."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "═══════════════════════════════════════════════════"
