from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "self-improvement" / "imp-context-engine.py"
LOG_PATH = ROOT / "logs" / "imp-context-bundles.json"

spec = importlib.util.spec_from_file_location("imp_context_engine", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _read_history() -> list:
    if not LOG_PATH.exists():
        return []
    try:
        return json.loads(LOG_PATH.read_text())
    except json.JSONDecodeError:
        return []


def test_context_engine_bundle():
    print("Testing Context Engine...")
    before = _read_history()
    bundle = module.build_context_bundle(limit_per_source=3, add_recent_logs=True)
    after = _read_history()

    assert len(after) >= len(before)
    assert bundle.get("created_at")
    assert bundle.get("source_count", 0) >= 1
    assert isinstance(bundle.get("sources"), list)
    assert "recent_logs" in bundle
    assert isinstance(bundle.get("missing_sources"), list)
    print("Context Engine Test Passed!")


if __name__ == "__main__":
    test_context_engine_bundle()
