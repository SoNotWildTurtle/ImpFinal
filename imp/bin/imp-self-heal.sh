#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Launch the IMP self-healer
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$PYTHON_BIN" "$ROOT/self-improvement/imp-self-healer.py" "$@"
