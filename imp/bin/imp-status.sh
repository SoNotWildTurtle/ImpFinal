#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"

echo "IMP AI System Status:"
exec "$PYTHON_BIN" "$IMP_ROOT/bin/imp-status.py" "$@"
