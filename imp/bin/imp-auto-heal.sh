#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Trigger automatic verification and healing
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$PYTHON_BIN" "$ROOT/self-improvement/imp-auto-heal.py" "$@"
