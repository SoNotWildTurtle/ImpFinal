#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"

ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

"$PYTHON_BIN" "$ROOT_DIR/core/imp-operator-ui.py" "$@"
