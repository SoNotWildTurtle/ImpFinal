#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"
#chmod +x <repo_root>/imp/bin/imp-status.sh

echo "IMP AI System Status:"

ps aux | grep -E "imp-execute|imp-learning-memory|imp-strategy-generator|imp-code-updater|imp-security-optimizer|imp-cluster-manager" | grep -v grep
