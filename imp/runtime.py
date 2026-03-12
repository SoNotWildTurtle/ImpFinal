from __future__ import annotations

import importlib.util
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any


IMP_ROOT = Path(__file__).resolve().parent
REPO_ROOT = IMP_ROOT.parent
LOG_DIR = IMP_ROOT / "logs"
CONFIG_DIR = IMP_ROOT / "config"
MODELS_DIR = IMP_ROOT / "models"
PID_FILE = LOG_DIR / "imp-pids.json"


def ensure_runtime_dirs() -> None:
    for path in (LOG_DIR, CONFIG_DIR, MODELS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def configure_file_logger(name: str, path: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def resolve_python() -> str:
    candidates = [
        os.getenv("IMP_PYTHON"),
        str(IMP_ROOT / ".venv" / "Scripts" / "python.exe"),
        str(IMP_ROOT / ".venv" / "bin" / "python"),
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    raise RuntimeError("Python interpreter not found. Set IMP_PYTHON or install Python.")

