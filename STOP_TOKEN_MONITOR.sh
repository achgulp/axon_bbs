#!/bin/bash
#═══════════════════════════════════════════════════════════════
# STOP TOKEN MONITOR
#═══════════════════════════════════════════════════════════════

PID_FILE="/tmp/token_monitor.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ No token monitor PID file found"
    echo "Monitor may not be running"
    exit 1
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    kill "$PID"
    rm "$PID_FILE"
    echo "✅ Token monitor stopped (PID: $PID)"
else
    echo "⚠️  Process $PID not running"
    rm "$PID_FILE"
    echo "Cleaned up stale PID file"
fi
