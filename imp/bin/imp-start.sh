#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
# remember to chmod +x imp/bin/imp-start.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
nohup "$PYTHON_BIN" "$ROOT/core/imp-execute.py" &
echo "Starting IMP AI System..."

nohup "$PYTHON_BIN" "$ROOT/core/imp-learning-memory.py" &
nohup "$PYTHON_BIN" "$ROOT/core/imp-strategy-generator.py" &
nohup "$PYTHON_BIN" "$ROOT/self-improvement/imp-code-updater.py" &
nohup "$PYTHON_BIN" "$ROOT/security/imp-security-optimizer.py" &
nohup "$PYTHON_BIN" "$ROOT/expansion/imp-cluster-manager.py" &

echo "IMP AI is now running."
