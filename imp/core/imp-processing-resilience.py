"""Resilience helpers for recovering from processing failures."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import importlib.util

CORE_DIR = Path(__file__).resolve().parent
ROOT = CORE_DIR.parent

# Reuse shared utility loaders
spec_utils = importlib.util.spec_from_file_location("imp_utils", CORE_DIR / "imp_utils.py")
imp_utils = importlib.util.module_from_spec(spec_utils)
spec_utils.loader.exec_module(imp_utils)
load_module = imp_utils.load_module
read_json = imp_utils.read_json
write_json = imp_utils.write_json

LOG_PATH = ROOT / "logs" / "imp-processing-resilience.json"
LOG_LIMIT = 500
Spec = Tuple[str, str, str]


def _serialise_spec(spec: Spec) -> Dict[str, str]:
    module, path_str, function = spec
    return {"module": module, "path": path_str, "function": function}


def _resolve_callable(spec: Spec):
    module_name, path_str, function_name = spec
    module = load_module(module_name, Path(path_str))
    return getattr(module, function_name)


class ProcessingResilience:
    """Capture failure telemetry and attempt sequential recovery."""

    def __init__(self) -> None:
        self.log_path = LOG_PATH
        if not self.log_path.exists():
            self.log_path.write_text("[]", encoding="utf-8")

    def _append(self, entry: Dict[str, Any]) -> None:
        history: List[Dict[str, Any]] = read_json(self.log_path, [])
        history.append(entry)
        if len(history) > LOG_LIMIT:
            history = history[-LOG_LIMIT:]
        write_json(self.log_path, history)

    def record_failures(
        self,
        group: str,
        failures: Sequence[Tuple[Spec, str]],
        *,
        duration: float,
        backlog: int,
        resource_score: float,
    ) -> None:
        if not failures:
            return
        self._append(
            {
                "event": "failure",
                "group": group,
                "failures": [
                    {"spec": _serialise_spec(spec), "error": error}
                    for spec, error in failures
                ],
                "duration": float(round(duration, 6)),
                "backlog": backlog,
                "resource_score": float(resource_score),
            }
        )

    def retry_failures(self, group: str, specs: Sequence[Spec]) -> Dict[str, Any]:
        if not specs:
            return {"resolved": 0, "remaining": []}

        resolved: List[Spec] = []
        remaining: List[Tuple[Spec, str]] = []
        for spec in specs:
            try:
                callable_obj = _resolve_callable(spec)
                callable_obj()
            except Exception as exc:  # pragma: no cover - stringified below
                remaining.append((spec, "{}".format(exc)))
            else:
                resolved.append(spec)

        if resolved or remaining:
            self._append(
                {
                    "event": "retry",
                    "group": group,
                    "resolved": [_serialise_spec(spec) for spec in resolved],
                    "remaining": [
                        {"spec": _serialise_spec(spec), "error": error}
                        for spec, error in remaining
                    ],
                }
            )

        return {
            "resolved": len(resolved),
            "resolved_specs": resolved,
            "remaining": [spec for spec, _ in remaining],
        }

    def record_unresolved(self, group: str, specs: Iterable[Spec]) -> None:
        outstanding = list(specs)
        if not outstanding:
            return
        self._append(
            {
                "event": "unresolved",
                "group": group,
                "outstanding": [_serialise_spec(spec) for spec in outstanding],
            }
        )

    def record_recovery(self, group: str, resolved: Sequence[Spec]) -> None:
        if not resolved:
            return
        self._append(
            {
                "event": "recovered",
                "group": group,
                "resolved": [_serialise_spec(spec) for spec in resolved],
            }
        )

