#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Ensure the goal chat terminal stays available
# If the chat process is not running, optionally restart it
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/logs/imp-chat-keepalive.log"
START_CHAT=1
if [ "$1" = "--no-start" ]; then
    START_CHAT=0
fi
if pgrep -f "imp-goal-chat.py" >/dev/null; then
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") chat running" >> "$LOG"
else
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") chat restarted" >> "$LOG"
    if [ $START_CHAT -eq 1 ]; then
        nohup "$PYTHON_BIN" "$ROOT/core/imp-goal-chat.py" --history >> "$ROOT/logs/imp-chat.log" 2>&1 &
    fi
fi
