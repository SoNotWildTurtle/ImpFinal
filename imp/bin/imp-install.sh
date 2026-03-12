#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/imp-env.sh"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REQUIREMENTS="$ROOT/requirements.txt"
VENV="$ROOT/.venv"
MODELS_DIR="$ROOT/models"
DEFAULT_GGUF="$MODELS_DIR/starcoder2-15b_Q4_K_M.gguf"
LEGACY_GGUF="$MODELS_DIR/starcoder2-15b.Q4_K_M.gguf"
DEFAULT_GGUF_URL=${IMP_GGUF_URL:-"https://huggingface.co/nold/starcoder2-15b-GGUF/resolve/main/starcoder2-15b_Q4_K_M.gguf?download=1"}

install_requirements() {
    "$PYTHON_BIN" -m pip install -r "$REQUIREMENTS" && return 0
    echo "Global install failed; attempting virtual environment..." >&2
    if command -v python3 >/dev/null 2>&1; then
        [ -d "$VENV" ] || python3 -m venv "$VENV" || return 1
    elif command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        [ -d "$VENV" ] || "$PYTHON_BIN" -m venv "$VENV" || return 1
    else
        return 1
    fi
    if [ -f "$VENV/bin/activate" ]; then
        . "$VENV/bin/activate" || return 1
    fi
    "$PYTHON_BIN" -m pip install -r "$REQUIREMENTS"
}

ensure_offline_model() {
    if ls "$MODELS_DIR"/*.gguf >/dev/null 2>&1; then
        echo "Offline GGUF model already present in $MODELS_DIR."
        return 0
    fi

    if [ -n "${IMP_GGUF_LOCAL_PATH:-}" ]; then
        if [ -f "${IMP_GGUF_LOCAL_PATH}" ]; then
            mkdir -p "$MODELS_DIR"
            cp "${IMP_GGUF_LOCAL_PATH}" "$DEFAULT_GGUF" && {
                echo "Copied offline model from IMP_GGUF_LOCAL_PATH to $DEFAULT_GGUF"
                cp "$DEFAULT_GGUF" "$LEGACY_GGUF" 2>/dev/null || true
                return 0
            }
            echo "Failed to copy model from IMP_GGUF_LOCAL_PATH=${IMP_GGUF_LOCAL_PATH}" >&2
        else
            echo "IMP_GGUF_LOCAL_PATH does not exist: ${IMP_GGUF_LOCAL_PATH}" >&2
        fi
    fi

    if [ "${IMP_SKIP_GGUF_DOWNLOAD:-0}" != "0" ]; then
        echo "Skipping offline model download (IMP_SKIP_GGUF_DOWNLOAD is set)."
        return 0
    fi

    mkdir -p "$MODELS_DIR"
    echo "Attempting to download base GGUF model for offline generation..."

    if command -v curl >/dev/null 2>&1; then
        if curl -L --fail "$DEFAULT_GGUF_URL" -o "$DEFAULT_GGUF"; then
            echo "Downloaded offline model to $DEFAULT_GGUF"
            cp "$DEFAULT_GGUF" "$LEGACY_GGUF" 2>/dev/null || true
            return 0
        else
            echo "curl download failed; trying alternate method" >&2
        fi
    fi

    if command -v wget >/dev/null 2>&1; then
        if wget -O "$DEFAULT_GGUF" "$DEFAULT_GGUF_URL"; then
            echo "Downloaded offline model to $DEFAULT_GGUF"
            cp "$DEFAULT_GGUF" "$LEGACY_GGUF" 2>/dev/null || true
            return 0
        else
            echo "wget download failed" >&2
        fi
    fi

    echo "Unable to download GGUF model automatically. Place the file at $DEFAULT_GGUF manually." >&2
}

if [ -f "$REQUIREMENTS" ]; then
    echo "Installing Python requirements..."
    install_requirements || { echo "Dependency installation failed" >&2; exit 1; }
fi

if [ -f "$VENV/bin/activate" ]; then
    . "$VENV/bin/activate"
fi

ensure_offline_model

"$ROOT/bin/imp-start.sh" || { echo "Startup failed" >&2; exit 1; }

# verify chat terminal remains available
"$ROOT/bin/imp-verify-chat.sh" >/dev/null 2>&1 || echo "Chat verification failed" >&2
