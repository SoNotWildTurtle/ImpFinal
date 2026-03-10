from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "self-improvement" / "imp-general-intelligence-review.py"
LOG_PATH = ROOT / "logs" / "imp-general-intelligence-review.json"

spec = importlib.util.spec_from_file_location("imp_general_review", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _load_history() -> list:
    try:
        return json.loads(LOG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def test_general_intelligence_review():
    print("Testing General Intelligence Review...")
    before = _load_history()
    entry = module.run_review()
    after = _load_history()

    assert len(after) >= len(before)
    assert after, "Expected at least one review history entry"
    assert after[-1]["checked_at"] == entry["checked_at"]
    assert entry["recommendations"], "Expected at least one recommendation"
    assert "operability_metrics" in entry

    trends = entry.get("trends", {})
    expected_keys = {
        "goal_completion_delta",
        "learning_entries_delta",
        "roadmap_coverage_delta",
        "evolution_entries_delta",
        "novel_average_delta",
        "operability_coverage_delta",
        "offline_updater_coverage_delta",
    }
    assert expected_keys.issubset(trends.keys())

    flags = entry.get("regression_flags")
    assert isinstance(flags, list)
    for flag in flags:
        assert isinstance(flag, str) and flag, "Regression flags must be non-empty strings"
    print("General Intelligence Review Test Passed!")


test_general_intelligence_review()
