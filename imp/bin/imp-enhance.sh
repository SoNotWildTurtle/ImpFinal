#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# Simple wrapper for IMP code enhancement
# Usage: imp-enhance.sh [offline|online|auto]
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-auto}"
"$PYTHON_BIN" "$ROOT/self-improvement/imp-code-updater.py" --mode "$MODE"
