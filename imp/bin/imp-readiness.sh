#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONIOENCODING="utf-8"
"$PYTHON_BIN" "$ROOT/self-improvement/imp-general-intelligence-review.py" "$@"
