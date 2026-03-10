from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "self-improvement" / "imp-module-operability.py"
LOG_PATH = ROOT / "logs" / "imp-module-operability.json"

spec = importlib.util.spec_from_file_location("imp_module_operability", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _load_history() -> list:
    try:
        return json.loads(LOG_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def test_module_operability_audit():
    print("Testing Module Operability Audit...")
    result = module.run_operability_audit()
    after = _load_history()

    assert after, "Expected operability history entries"
    assert after[-1]["checked_at"] == result["checked_at"]
    assert 0 <= result["coverage"] <= 100
    assert result["total_checks"] >= result["passed_checks"]
    assert result["domains"], "Expected domain-level operability details"

    startup = result["domains"].get("startup-consistency", {})
    if startup:
        assert any(check.get("type") == "content" for check in startup.get("checks", []))

    offline = result["domains"].get("offline-updater-readiness", {})
    if offline:
        assert any(check.get("type") == "glob" for check in offline.get("checks", []))

    methodology = result["domains"].get("methodology-readiness", {})
    assert methodology, "Expected methodology-readiness domain from plan.json"
    assert any(check.get("type") == "source" for check in methodology.get("checks", []))
    assert any(check.get("type") == "keyword" for check in methodology.get("checks", []))
    print("Module Operability Audit Test Passed!")


def test_operability_goal_generation():
    print("Testing Operability Goal Generation...")
    goals_file = ROOT / "logs" / "imp-goals.json"
    original_goals = goals_file.read_text() if goals_file.exists() else "[]"
    fake_profiles = [
        {
            "name": "fake-domain",
            "required_paths": ["core/definitely-missing-module.py"],
            "required_tests": ["tests/definitely-missing-test.py"],
            "required_content": [
                {
                    "path": "bin/imp-start.sh",
                    "contains": ["this-pattern-should-never-exist"],
                    "match": "all",
                }
            ],
            "required_globs": ["models/definitely-missing-model*.gguf"],
        }
    ]
    try:
        result = module.run_operability_audit(
            add_goals=True,
            profiles=fake_profiles,
            include_methodology=False,
        )
        updates = result.get("goal_updates", [])
        assert len(updates) == 4

        again = module.run_operability_audit(
            add_goals=True,
            profiles=fake_profiles,
            include_methodology=False,
        )
        assert len(again.get("goal_updates", [])) == 0
    finally:
        goals_file.write_text(original_goals)
    print("Operability Goal Generation Test Passed!")


if __name__ == "__main__":
    test_module_operability_audit()
    test_operability_goal_generation()
