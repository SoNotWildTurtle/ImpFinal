#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Loop to keep the goal chat terminal alive
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/logs/imp-chat-keepalive.log"
while true; do
    if command -v tmux >/dev/null; then
        if ! tmux has-session -t impchat 2>/dev/null; then
            tmux new-session -d -s impchat "$ROOT/bin/imp-chat.sh"
            echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") tmux session started" >> "$LOG"
        else
            echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") tmux session active" >> "$LOG"
        fi
    elif command -v screen >/dev/null; then
        if ! screen -list | grep -q "impchat"; then
            screen -dmS impchat "$ROOT/bin/imp-chat.sh"
            echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") screen session started" >> "$LOG"
        else
            echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") screen session active" >> "$LOG"
        fi
    else
        "$ROOT/bin/imp-verify-chat.sh"
    fi
    sleep 60
done
