#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export IMP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export IMP_REPO_ROOT="$(cd "$IMP_ROOT/.." && pwd)"
export IMP_LOG_DIR="${IMP_LOG_DIR:-$IMP_ROOT/logs}"
export IMP_CONFIG_DIR="${IMP_CONFIG_DIR:-$IMP_ROOT/config}"
export IMP_MODELS_DIR="${IMP_MODELS_DIR:-$IMP_ROOT/models}"

mkdir -p "$IMP_LOG_DIR" "$IMP_CONFIG_DIR" "$IMP_MODELS_DIR"

if [ -n "${IMP_PYTHON:-}" ] && [ -x "${IMP_PYTHON}" ]; then
    export PYTHON_BIN="$IMP_PYTHON"
elif [ -x "$IMP_ROOT/.venv/bin/python" ]; then
    export PYTHON_BIN="$IMP_ROOT/.venv/bin/python"
elif [ -x "$IMP_ROOT/.venv/Scripts/python.exe" ]; then
    export PYTHON_BIN="$IMP_ROOT/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    export PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    export PYTHON_BIN="$(command -v python)"
else
    echo "Python interpreter not found. Set IMP_PYTHON or install Python." >&2
    return 1 2>/dev/null || exit 1
fi

export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -n "${IMP_PYTHON:-}" ]; then
    PYTHON_BIN="$IMP_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Python interpreter not found. Set IMP_PYTHON or install Python." >&2
    exit 1
fi
