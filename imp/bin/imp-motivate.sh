#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Simple wrapper to run the motivation engine
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$PYTHON_BIN" "$SCRIPT_DIR/../core/imp-motivation.py"
