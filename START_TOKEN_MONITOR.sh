#!/bin/bash
#═══════════════════════════════════════════════════════════════
# START TOKEN MONITOR - Launch background token monitoring
#═══════════════════════════════════════════════════════════════
# Launches token monitor in background with nohup
# Usage: ./START_TOKEN_MONITOR.sh
#═══════════════════════════════════════════════════════════════

SCRIPT_DIR="/path/to/axon_bbs"
MONITOR_SCRIPT="$SCRIPT_DIR/TOKEN_MONITOR.sh"
PID_FILE="/tmp/token_monitor.pid"
LOG_FILE="/tmp/token_monitor.log"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "⚠️  Token monitor already running (PID: $OLD_PID)"
        echo "To stop: kill $OLD_PID"
        exit 1
    else
        echo "Removing stale PID file..."
        rm "$PID_FILE"
    fi
fi

# Make executable
chmod +x "$MONITOR_SCRIPT"

# Launch in background with nohup
nohup "$MONITOR_SCRIPT" > "$LOG_FILE" 2>&1 &
MONITOR_PID=$!

# Save PID
echo "$MONITOR_PID" > "$PID_FILE"

echo "═══════════════════════════════════════════════════"
echo "✅ TOKEN MONITOR STARTED"
echo "═══════════════════════════════════════════════════"
echo "PID: $MONITOR_PID"
echo "Log: $LOG_FILE"
echo "Reminders: /tmp/claude_token_reminders.log"
echo ""
echo "Monitor will check every 30 minutes"
echo "Notifications sent to screen session 'Claude'"
echo ""
echo "To stop: kill $MONITOR_PID"
echo "       or: kill \$(cat $PID_FILE)"
echo "═══════════════════════════════════════════════════"
