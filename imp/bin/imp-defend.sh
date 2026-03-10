#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Run the automated defense cycle
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$PYTHON_BIN" "$ROOT/security/imp-automated-defense.py" "$@"
