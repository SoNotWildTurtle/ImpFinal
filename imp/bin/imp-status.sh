#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"

echo "IMP AI System Status:"
if [ -f "$IMP_LOG_DIR/imp-pids.json" ]; then
    cat "$IMP_LOG_DIR/imp-pids.json"
else
    echo "No PID file found at $IMP_LOG_DIR/imp-pids.json"
fi
