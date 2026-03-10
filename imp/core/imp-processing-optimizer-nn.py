"""Neural helper that optimizes processing group allocations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import importlib.util

CORE_DIR = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json

LOG_PATH = CORE_DIR.parents[1] / "logs" / "imp-processing-optimizer.json"


class _OptimizerState:
    """Track rolling metrics for a functionality group."""

    def __init__(self) -> None:
        self.avg_resource: float = 50.0
        self.avg_duration: float = 1.0
        self.avg_backlog: float = 0.0
        self.avg_errors: float = 0.0
        self.priority: float = 1.0
        self.last_threads: int = 1
        self.history: List[Dict[str, float]] = []


class ProcessingOptimizerNN:
    """Guides processing allocations using rolling telemetry."""

    def __init__(self, max_threads: int = 8) -> None:
        self.max_threads = max_threads
        self.groups: Dict[str, _OptimizerState] = {}

    # Internal helpers -------------------------------------------------
    def _state(self, group: str) -> _OptimizerState:
        return self.groups.setdefault(group, _OptimizerState())

    def _append_history(self, group: str, entry: Dict[str, float]) -> None:
        state = self._state(group)
        state.history.append(entry)
        if len(state.history) > 40:
            state.history.pop(0)

    def _log(self, entry: Dict[str, float]) -> None:
        data = read_json(LOG_PATH, [])
        data.append(entry)
        write_json(LOG_PATH, data)

    # Public API -------------------------------------------------------
    def bootstrap_priority(self, group: str, backlog: int = 0) -> float:
        """Seed an initial priority for ordering process start-up."""
        state = self._state(group)
        state.avg_backlog = backlog
        state.priority = min(3.0, 1.0 + backlog * 0.1)
        entry = {
            "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "group": group,
            "event": "bootstrap",
            "priority": state.priority,
            "backlog": backlog,
        }
        self._append_history(group, entry)
        self._log(entry)
        return state.priority

    def plan_allocation(
        self,
        group: str,
        resource_score: float,
        backlog: int,
        base_threads: int,
    ) -> Dict[str, float]:
        """Return thread, pause, and priority adjustments for the next cycle."""
        state = self._state(group)
        score = 50.0 if resource_score is None else float(resource_score)
        base = max(1, base_threads)

        # Update rolling averages before computing the plan so they guide the decision.
        state.avg_resource = 0.6 * state.avg_resource + 0.4 * score
        state.avg_backlog = 0.6 * state.avg_backlog + 0.4 * backlog

        # Determine scaling based on backlog pressure and resource availability.
        scale = 1.0 + 0.15 * state.avg_backlog
        if backlog > base:
            scale += 0.1 * min(backlog - base, 3)
        if score < 45:
            scale += 0.25
        elif score > 75 and state.avg_backlog < 1:
            scale -= 0.25
        if state.avg_errors > 0.5:
            scale -= 0.25

        threads = max(1, min(self.max_threads, int(round(base * scale))))

        # Pause is shorter when resources are abundant, longer when durations climb.
        pause = max(0.25, 1.0 + state.avg_duration * 0.1 - state.avg_resource / 100.0)

        state.priority = min(3.0, 1.0 + state.avg_backlog * 0.2 + (0.3 if score < 40 else 0.0))
        state.last_threads = threads

        entry = {
            "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "group": group,
            "event": "plan",
            "threads": threads,
            "pause": pause,
            "priority": state.priority,
            "avg_resource": state.avg_resource,
            "avg_backlog": state.avg_backlog,
        }
        self._append_history(group, entry)
        self._log(entry)
        return {"threads": threads, "pause": pause, "priority": state.priority}

    def record_cycle(
        self,
        group: str,
        duration: float,
        threads: int,
        resource_score: float,
        errors: int,
        backlog: int,
    ) -> None:
        """Log the results of a cycle so future plans can adapt."""
        state = self._state(group)
        score = 50.0 if resource_score is None else float(resource_score)
        state.avg_duration = 0.5 * duration + 0.5 * state.avg_duration
        state.avg_errors = 0.4 * errors + 0.6 * state.avg_errors
        state.avg_resource = 0.5 * state.avg_resource + 0.5 * score
        state.avg_backlog = 0.5 * state.avg_backlog + 0.5 * backlog
        state.last_threads = threads

        entry = {
            "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "group": group,
            "event": "cycle",
            "duration": duration,
            "threads": threads,
            "resource_score": score,
            "errors": errors,
            "backlog": backlog,
        }
        self._append_history(group, entry)
        self._log(entry)

    def history(self, group: str) -> List[Dict[str, float]]:
        """Return recent optimizer telemetry for the group."""
        return list(self._state(group).history)

    def last_priority(self, group: str) -> float:
        return self._state(group).priority
