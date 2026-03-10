from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, List


def read_json(path: Path, default: Any):
    """Return data from JSON file or default if missing/invalid."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, data: Any) -> None:
    """Write data as JSON to path, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def load_module(name: str, path: Path):
    """Dynamically load a module from the given path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _fallback_generator(context: str) -> Callable[[str], List[dict]]:
    """Return a lightweight text generator that never leaves the machine."""

    prefix = context.strip() or "IMP"

    def _generate(prompt: str, max_length: int = 512, num_return_sequences: int = 1, **_: Any) -> List[dict]:
        lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        body = " ".join(lines) or "No additional context provided."
        snippet = body[: max_length]
        text = f"{prefix} insight: {snippet}"
        count = max(1, num_return_sequences)
        return [{"generated_text": text} for _ in range(count)]

    return _generate


def resolve_text_generator(context: str, model: str = "gpt2") -> Callable[[str], List[dict]]:
    """Return a text generator that favours offline safety."""

    if os.getenv("IMP_USE_TRANSFORMERS"):
        try:  # Import lazily so modules without transformers still load quickly
            from transformers import pipeline  # type: ignore
        except Exception:  # pragma: no cover - dependency may be absent
            pipeline = None  # type: ignore
        else:
            try:
                generator = pipeline(
                    "text-generation",
                    model=model,
                    local_files_only=True,
                )

                def _wrapped(prompt: str, max_length: int = 512, num_return_sequences: int = 1, **kwargs: Any) -> List[dict]:
                    return generator(prompt, max_length=max_length, num_return_sequences=num_return_sequences, **kwargs)  # type: ignore[return-value]

                return _wrapped
            except Exception:
                pass

    return _fallback_generator(context)
