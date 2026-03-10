#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Monitor network connections
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$PYTHON_BIN" "$ROOT/security/imp-network-monitor.py" "$@"
