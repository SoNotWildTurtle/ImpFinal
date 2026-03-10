from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"

DIRECTOR = _load("director", ROOT / "self-improvement" / "imp-success-director.py")
GOALS = _load("goal_manager", ROOT / "core" / "imp-goal-manager.py")


def _read(path: Path, default):
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                return default
    return default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def _backup(paths):
    return {path: _read(path, None) for path in paths}


def _restore(backups):
    for path, data in backups.items():
        if data is None:
            if path.exists():
                path.unlink()
        else:
            _write(path, data)


def _seed_logs():
    _write(
        LOG_DIR / "imp-goals.json",
        [
            {
                "id": "existing",
                "goal": "Stabilise baseline systems",
                "term": "long-term",
                "priority": "low",
                "status": "pending",
                "created_at": "2024-01-01T00:00:00Z",
                "category": "general",
            }
        ],
    )
    _write(LOG_DIR / "imp-learning-memory.json", [])
    _write(
        LOG_DIR / "imp-roadmap-progress.json",
        {"Resilience": {"imp/security/example.py": False}},
    )
    _write(
        LOG_DIR / "imp-evolution-log.json",
        [
            {"novel": 0.2, "summary": "baseline"},
        ],
    )
    _write(LOG_DIR / "imp-novel-neuron-experiments.json", [])
    _write(
        LOG_DIR / "imp-module-operability.json",
        [
            {
                "checked_at": "2026-02-25T00:00:00Z",
                "coverage": 85.0,
                "failed_checks": 3,
                "domains": {
                    "offline-updater-readiness": {
                        "coverage": 50.0,
                    }
                },
            }
        ],
    )


def main():
    print("Testing Success Director...")

    log_paths = [
        LOG_DIR / "imp-goals.json",
        LOG_DIR / "imp-learning-memory.json",
        LOG_DIR / "imp-roadmap-progress.json",
        LOG_DIR / "imp-evolution-log.json",
        LOG_DIR / "imp-novel-neuron-experiments.json",
        LOG_DIR / "imp-general-intelligence-review.json",
        LOG_DIR / "imp-module-operability.json",
        LOG_DIR / "imp-context-bundles.json",
        LOG_DIR / "imp-success-plan.json",
    ]

    backups = _backup(log_paths)
    try:
        _seed_logs()
        result = DIRECTOR.build_success_plan(add_goals=True)
        assert result["plan"]["actions"], "Success plan should include actions"
        assert result["goals_added"], "New actions should add follow-up goals"
        assert result["plan"]["context_sources"] >= 1
        assert result["plan"]["context_timestamp"]
        assert any(
            action.get("category") == "operability" for action in result["plan"]["actions"]
        ), "Expected operability action from module operability metrics"

        stored_goals = GOALS.get_existing_goals()
        assert any(goal["goal"] in result["goals_added"] for goal in stored_goals)

        history = _read(LOG_DIR / "imp-success-plan.json", [])
        assert history, "Success plan log should record at least one entry"
    finally:
        _restore(backups)

    print("Success Director Test Passed!")


if __name__ == "__main__":
    main()
