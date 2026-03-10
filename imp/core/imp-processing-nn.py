"""ProcessingManagerNN guides concurrency for functionality groups."""

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

LOG_PATH = CORE_DIR.parents[1] / "logs" / "imp-processing-log.json"


class GroupState:
    def __init__(self) -> None:
        self.threads: int = 1
        self.avg_duration: float = 1.0
        self.errors: int = 0
        self.history: List[Dict[str, float]] = []


class ProcessingManagerNN:
    """Lightweight controller that allocates threads per functionality group."""

    def __init__(self, max_threads: int = 4) -> None:
        self.max_threads = max_threads
        self.groups: Dict[str, GroupState] = {}

    # Internal helpers -------------------------------------------------
    def _state(self, group: str) -> GroupState:
        return self.groups.setdefault(group, GroupState())

    def _append_history(self, group: str, entry: Dict[str, float]) -> None:
        state = self._state(group)
        state.history.append(entry)
        if len(state.history) > 20:
            state.history.pop(0)

    def _log_entry(self, entry: Dict[str, float]) -> None:
        data = read_json(LOG_PATH, [])
        data.append(entry)
        write_json(LOG_PATH, data)

    # Public API -------------------------------------------------------
    def recommend_threads(self, group: str, resource_score: float, backlog: int = 0) -> int:
        """Return thread count based on resource headroom and backlog size."""
        state = self._state(group)
        score = resource_score if resource_score is not None else 50.0
        threads = state.threads

        if score < 35:
            bump = 2 if backlog > 1 else 1
            threads = min(self.max_threads, threads + bump)
        elif score < 55 and backlog > 0:
            threads = min(self.max_threads, threads + 1)
        elif score > 75:
            threads = max(1, threads - 1)

        state.threads = threads
        return threads

    def recommend_pause(self, group: str) -> float:
        """Return a short pause between cycles based on errors and duration."""
        state = self._state(group)
        pause = 1.0
        if state.avg_duration > 2.0:
            pause += 1.0
        if state.errors:
            pause += min(state.errors, 3)
        return pause

    def record_cycle(
        self,
        group: str,
        duration: float,
        threads: int,
        resource_score: float,
        errors: int,
        backlog: int,
    ) -> None:
        """Update moving averages and persist telemetry for analysis."""
        state = self._state(group)
        alpha = 0.6
        state.avg_duration = alpha * duration + (1 - alpha) * state.avg_duration
        state.errors = errors
        entry = {
            "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "group": group,
            "duration": duration,
            "threads": threads,
            "resource_score": resource_score,
            "errors": errors,
            "backlog": backlog,
        }
        self._append_history(group, entry)
        self._log_entry(entry)

    def history(self, group: str) -> List[Dict[str, float]]:
        """Return recent telemetry for a group."""
        return list(self._state(group).history)
