#!/bin/bash
#═══════════════════════════════════════════════════════════════
# TOKEN USAGE MONITOR - Background Process
#═══════════════════════════════════════════════════════════════
# Monitors Claude Code session and sends reminders to check tokens
# Usage: nohup ./TOKEN_MONITOR.sh &
#═══════════════════════════════════════════════════════════════

SCREEN_SESSION="Claude"
CHECK_INTERVAL=1800  # 30 minutes in seconds
REMINDER_FILE="/tmp/claude_token_reminders.log"

# Initialize log
echo "Token Monitor started: $(date)" > "$REMINDER_FILE"

# Function to send notification to Claude screen
send_notification() {
    local message="$1"
    if screen -ls 2>/dev/null | grep -q "$SCREEN_SESSION"; then
        screen -S "$SCREEN_SESSION" -X stuff "$message\n"
        echo "$(date): Sent notification: $message" >> "$REMINDER_FILE"
    else
        echo "$(date): Screen session '$SCREEN_SESSION' not found" >> "$REMINDER_FILE"
    fi
}

# Send startup notification
send_notification "🟢 TOKEN_MONITOR: Started. Will check every 30min."

# Counter for elapsed time
elapsed_minutes=0

# Main monitoring loop
while true; do
    sleep "$CHECK_INTERVAL"
    elapsed_minutes=$((elapsed_minutes + 30))

    # Send reminder based on elapsed time
    if [ $elapsed_minutes -eq 30 ]; then
        send_notification "⏱️  TOKEN_CHECK: 30min mark - Quick token check?"
    elif [ $elapsed_minutes -eq 60 ]; then
        send_notification "⏱️  TOKEN_CHECK: 1 hour mark - How are tokens?"
    elif [ $elapsed_minutes -eq 90 ]; then
        send_notification "⚠️  TOKEN_CHECK: 1.5 hours - Likely approaching 80% - Consider saving!"
    elif [ $elapsed_minutes -eq 120 ]; then
        send_notification "🔴 TOKEN_CRITICAL: 2 hours - SAVE SESSION SUMMARY NOW!"
    else
        # Every 30 minutes after 2 hours
        send_notification "⏱️  TOKEN_CHECK: ${elapsed_minutes}min elapsed - Check usage"
    fi
done
