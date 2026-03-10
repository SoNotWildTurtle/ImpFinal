#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$PYTHON_BIN" "$ROOT/core/imp-speech-to-text.py" "$@"
