#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
#remember to chmod +x <repo_root>/imp/bin/imp-stop.sh

echo "🛑 Stopping IMP AI System..."
pkill -f imp-execute.py
pkill -f imp-learning-memory.py
pkill -f imp-strategy-generator.py
pkill -f imp-code-updater.py
pkill -f imp-security-optimizer.py
pkill -f imp-cluster-manager.py

echo "IMP AI has been stopped."
