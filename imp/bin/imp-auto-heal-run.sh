#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Run self-healing followed by a core functionality check
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$PYTHON_BIN" "$SCRIPT_DIR/../self-improvement/imp-auto-heal.py"
"$PYTHON_BIN" "$SCRIPT_DIR/../tests/test-core-functions.py" >/dev/null
