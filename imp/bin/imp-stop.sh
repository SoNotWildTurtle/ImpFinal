#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"

echo "Stopping IMP AI System..."
exec "$PYTHON_BIN" "$IMP_ROOT/bin/imp-stop.py" "$@"
