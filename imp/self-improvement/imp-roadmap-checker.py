"""Roadmap checker with coverage summaries and directory metrics."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "notes" / "imp-research-roadmap.txt"
PROGRESS_LOG = ROOT / "logs" / "imp-roadmap-progress.json"
HISTORY_LOG = ROOT / "logs" / "imp-roadmap-progress-history.json"

GOALS_KEY = "goals"
SUMMARY_KEY = "summary"
DIRECTORY_KEY = "directories"

UNRESOLVED = "unresolved"
MODULE_PATTERN = re.compile(r"imp-[\w-]+\.py")
MODULE_DIRECTORIES = [
    ("core", ROOT / "core"),
    ("self-improvement", ROOT / "self-improvement"),
    ("security", ROOT / "security"),
    ("expansion", ROOT / "expansion"),
    ("communication", ROOT / "communication"),
]


def _coverage(completed: int, total: int) -> float:
    """Return percentage coverage rounded to two decimals."""

    if total == 0:
        return 0.0
    return round((completed / total) * 100.0, 2)


def _resolve_module(module: str, cache: Dict[str, Tuple[bool, str]]) -> Tuple[bool, str]:
    """Return whether the module exists and the owning directory label."""

    if module in cache:
        return cache[module]

    for label, base in MODULE_DIRECTORIES:
        candidate = base / module
        if candidate.exists():
            cache[module] = (True, label)
            return cache[module]

    cache[module] = (False, UNRESOLVED)
    return cache[module]


def _parse_goals(text: str) -> Tuple[Dict[str, Dict[str, bool]], Dict[str, str]]:
    """Extract roadmap goals and track module presence and directories."""

    goals: Dict[str, Dict[str, bool]] = {}
    module_directories: Dict[str, str] = {}
    cache: Dict[str, Tuple[bool, str]] = {}

    in_goals = False
    current_goal: str | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if not in_goals:
            if stripped.startswith("5. Next Generation Goals"):
                in_goals = True
            continue

        if stripped.startswith("6. Implementation Plan"):
            break

        if re.match(r"^\d+\.\s", stripped):
            current_goal = re.sub(r"^\d+\.\s*", "", stripped)
            goals[current_goal] = {}
            continue

        if not current_goal:
            continue

        modules = MODULE_PATTERN.findall(stripped)
        for module_name in modules:
            exists, directory = _resolve_module(module_name, cache)
            goals[current_goal][module_name] = exists
            module_directories[module_name] = directory

    return goals, module_directories


def _build_summary(goals: Dict[str, Dict[str, bool]]) -> Dict[str, object]:
    """Compute aggregate coverage details for roadmap goals."""

    total_modules = 0
    total_completed = 0
    details: Dict[str, Dict[str, object]] = {}

    for goal, modules in goals.items():
        goal_total = len(modules)
        goal_completed = sum(1 for present in modules.values() if present)
        missing = sorted(name for name, present in modules.items() if not present)

        total_modules += goal_total
        total_completed += goal_completed

        details[goal] = {
            "modules_total": goal_total,
            "modules_completed": goal_completed,
            "modules_missing": missing,
            "coverage": _coverage(goal_completed, goal_total),
        }

    total_missing = total_modules - total_completed

    return {
        "goals_tracked": len(goals),
        "modules_total": total_modules,
        "modules_completed": total_completed,
        "modules_missing": total_missing,
        "coverage": _coverage(total_completed, total_modules),
        "details": details,
    }


def _build_directory_summary(
    goals: Dict[str, Dict[str, bool]],
    module_directories: Dict[str, str],
) -> Dict[str, Dict[str, object]]:
    """Summarise completion metrics by module directory."""

    summary: Dict[str, Dict[str, object]] = defaultdict(
        lambda: {
            "modules_total": 0,
            "modules_completed": 0,
            "modules_missing": [],
        }
    )

    for modules in goals.values():
        for module_name, present in modules.items():
            directory = module_directories.get(module_name, UNRESOLVED)
            entry = summary[directory]
            entry["modules_total"] += 1
            if present:
                entry["modules_completed"] += 1
            else:
                entry["modules_missing"].append(module_name)

    for entry in summary.values():
        entry["modules_missing"].sort()
        entry["coverage"] = _coverage(entry["modules_completed"], entry["modules_total"])

    return dict(summary)


def _timestamp() -> str:
    """Return the current UTC timestamp without microseconds."""

    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _collect_missing_modules(goals: Dict[str, Dict[str, bool]]) -> List[str]:
    """Return a sorted list of modules that have not been implemented."""

    return sorted(
        module_name
        for modules in goals.values()
        for module_name, present in modules.items()
        if not present
    )


def _load_history() -> List[Dict[str, object]]:
    """Load the roadmap history log if it exists."""

    if HISTORY_LOG.exists():
        try:
            with open(HISTORY_LOG, encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
    return []


def _append_history(
    goals: Dict[str, Dict[str, bool]], summary: Dict[str, object]
) -> Dict[str, object]:
    """Append a snapshot of the current summary to the history log."""

    entry = {
        "timestamp": _timestamp(),
        "coverage": summary.get("coverage", 0.0),
        "modules_total": summary.get("modules_total", 0),
        "modules_completed": summary.get("modules_completed", 0),
        "modules_missing": summary.get("modules_missing", 0),
        "missing_modules": _collect_missing_modules(goals),
    }

    history = _load_history()
    history.append(entry)

    HISTORY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_LOG, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=4)

    return entry


def check_progress() -> Dict[str, object]:
    """Parse the roadmap and persist goal coverage analytics."""

    if ROADMAP.exists():
        text = ROADMAP.read_text()
        goals, module_directories = _parse_goals(text)
    else:
        goals, module_directories = {}, {}

    summary = _build_summary(goals)
    history_entry = _append_history(goals, summary)
    summary["checked_at"] = history_entry["timestamp"]
    directories = _build_directory_summary(goals, module_directories)

    data = {
        GOALS_KEY: goals,
        SUMMARY_KEY: summary,
        DIRECTORY_KEY: directories,
    }

    PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_LOG, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)

    return data


if __name__ == "__main__":
    check_progress()
