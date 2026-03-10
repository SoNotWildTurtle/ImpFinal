#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
"$PYTHON_BIN" "$SCRIPT_DIR/../core/imp-processing-analytics.py" "$@"
