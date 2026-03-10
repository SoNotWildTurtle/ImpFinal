"""Aggregate IMP's self-knowledge to review general intelligence readiness."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
IMP_DIR = ROOT / "imp"
LOG_DIR = IMP_DIR / "logs"
REVIEW_LOG = LOG_DIR / "imp-general-intelligence-review.json"


def _load(name: str, path: Path):
    """Dynamically load a helper module."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_utils = _load("imp_utils", IMP_DIR / "core" / "imp_utils.py")
read_json = _utils.read_json
write_json = _utils.write_json


def _timestamp() -> str:
    """Return a UTC timestamp without microseconds."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _goal_metrics(goals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarise goal completion and priority balance."""
    status_counts = Counter(entry.get("status", "unknown") for entry in goals)
    priority_counts = Counter(entry.get("priority", "unspecified") for entry in goals)
    total = sum(status_counts.values())
    completed = status_counts.get("completed", 0)
    coverage = round((completed / total) * 100.0, 2) if total else 0.0
    return {
        "total": total,
        "status": dict(status_counts),
        "priorities": dict(priority_counts),
        "completion_rate": coverage,
    }


def _learning_memory_metrics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return counts of insights by category and status."""
    category_counts = Counter(entry.get("category", "uncategorised") for entry in entries)
    status_counts = Counter(entry.get("status", "unknown") for entry in entries)
    recent = entries[-5:] if entries else []
    return {
        "entries": len(entries),
        "categories": dict(category_counts),
        "status": dict(status_counts),
        "recent": recent,
    }


def _roadmap_metrics(roadmap: Dict[str, Dict[str, bool]]) -> Dict[str, Any]:
    """Calculate roadmap coverage percentages."""
    modules_total = 0
    modules_completed = 0
    gaps: List[Tuple[str, str]] = []
    for goal, modules in roadmap.items():
        for module_name, present in modules.items():
            modules_total += 1
            if present:
                modules_completed += 1
            else:
                gaps.append((goal, module_name))
    coverage = round((modules_completed / modules_total) * 100.0, 2) if modules_total else 0.0
    return {
        "goals_tracked": len(roadmap),
        "modules_total": modules_total,
        "modules_completed": modules_completed,
        "coverage": coverage,
        "gaps": gaps,
    }


def _evolution_metrics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarise neural evolution progress."""
    total_entries = len(entries)
    if not entries:
        return {
            "entries": 0,
            "latest": {},
            "novel_average": 0.0,
        }
    novel_values = [float(entry.get("novel", 0)) for entry in entries]
    average_novel = round(sum(novel_values) / total_entries, 2)
    return {
        "entries": total_entries,
        "latest": entries[-1],
        "novel_average": average_novel,
    }


def _operability_metrics(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarise latest module operability coverage and key domain coverage."""
    if not history:
        return {"coverage": 0.0, "failed_checks": 0, "domains": {}}
    latest = history[-1] if isinstance(history[-1], dict) else {}
    domains = latest.get("domains", {}) if isinstance(latest, dict) else {}
    domain_coverage: Dict[str, float] = {}
    if isinstance(domains, dict):
        for name, info in domains.items():
            if isinstance(info, dict):
                domain_coverage[str(name)] = float(info.get("coverage", 0.0))
    return {
        "coverage": float(latest.get("coverage", 0.0)),
        "failed_checks": int(latest.get("failed_checks", 0)),
        "domains": domain_coverage,
    }


def _trend_snapshot(previous: Optional[Dict[str, Any]], current: Dict[str, Any]) -> Dict[str, float]:
    """Calculate metric deltas compared to the previous review entry."""
    if not previous:
        return {
            "goal_completion_delta": 0.0,
            "learning_entries_delta": 0,
            "roadmap_coverage_delta": 0.0,
            "evolution_entries_delta": 0,
            "novel_average_delta": 0.0,
            "operability_coverage_delta": 0.0,
            "offline_updater_coverage_delta": 0.0,
        }

    prev_goal = previous.get("goal_metrics", {})
    prev_learning = previous.get("learning_metrics", {})
    prev_roadmap = previous.get("roadmap_metrics", {})
    prev_evolution = previous.get("evolution_metrics", {})
    prev_operability = previous.get("operability_metrics", {})
    prev_domains = prev_operability.get("domains", {}) if isinstance(prev_operability, dict) else {}
    current_operability = current.get("operability_metrics", {})
    current_domains = current_operability.get("domains", {}) if isinstance(current_operability, dict) else {}

    return {
        "goal_completion_delta": round(
            current["goal_metrics"].get("completion_rate", 0.0)
            - prev_goal.get("completion_rate", 0.0),
            2,
        ),
        "learning_entries_delta": int(
            current["learning_metrics"].get("entries", 0) - prev_learning.get("entries", 0)
        ),
        "roadmap_coverage_delta": round(
            current["roadmap_metrics"].get("coverage", 0.0) - prev_roadmap.get("coverage", 0.0),
            2,
        ),
        "evolution_entries_delta": int(
            current["evolution_metrics"].get("entries", 0) - prev_evolution.get("entries", 0)
        ),
        "novel_average_delta": round(
            current["evolution_metrics"].get("novel_average", 0.0)
            - prev_evolution.get("novel_average", 0.0),
            2,
        ),
        "operability_coverage_delta": round(
            current_operability.get("coverage", 0.0) - prev_operability.get("coverage", 0.0),
            2,
        ),
        "offline_updater_coverage_delta": round(
            current_domains.get("offline-updater-readiness", 0.0)
            - prev_domains.get("offline-updater-readiness", 0.0),
            2,
        ),
    }


def _regression_flags(previous: Optional[Dict[str, Any]], entry: Dict[str, Any]) -> List[str]:
    """Highlight significant regressions compared to the previous review."""
    if not previous:
        return []

    trends = entry.get("trends", {})
    flags: List[str] = []
    if trends.get("goal_completion_delta", 0.0) < -5:
        flags.append("Goal completion rate dropped by more than five percent since the last review.")
    if trends.get("learning_entries_delta", 0) < 0:
        flags.append("Learning memory contains fewer entries than the previous review.")
    if trends.get("roadmap_coverage_delta", 0.0) < 0:
        flags.append("Roadmap coverage decreased; investigate recently removed modules or goals.")
    if trends.get("evolution_entries_delta", 0) < 0:
        flags.append("Evolution log entries regressed; ensure evolution snapshots continue running.")
    if trends.get("novel_average_delta", 0.0) < -0.1:
        flags.append("Novel neuron average declined; schedule experiments to diversify the network.")
    if trends.get("operability_coverage_delta", 0.0) < 0:
        flags.append("Operability coverage decreased; investigate failed module/test readiness checks.")
    if trends.get("offline_updater_coverage_delta", 0.0) < 0:
        flags.append("Offline updater readiness regressed; verify GGUF model assets and updater fallback paths.")
    return flags


def _load_log(name: str, default: Any) -> Any:
    """Load a log file from the logs directory."""
    path = LOG_DIR / name
    return read_json(path, default)


def _recommendations(
    goal_metrics: Dict[str, Any],
    learning_metrics: Dict[str, Any],
    roadmap_metrics: Dict[str, Any],
    evolution_metrics: Dict[str, Any],
    operability_metrics: Dict[str, Any],
) -> List[str]:
    """Generate qualitative recommendations from the collected metrics."""
    recs: List[str] = []

    if goal_metrics["total"] and goal_metrics["completion_rate"] < 50:
        recs.append(
            "Prioritise clearing pending goals or re-evaluating their scope so completion stays above 50%."
        )
    if not learning_metrics["entries"]:
        recs.append("Capture fresh insights in the learning memory after significant actions or experiments.")
    elif learning_metrics["entries"] < 5:
        recs.append("Expand learning memory entries to build a richer base for metacognitive analysis.")
    if roadmap_metrics["coverage"] < 100:
        outstanding = [module for _, module in roadmap_metrics["gaps"][:3]]
        if outstanding:
            recs.append("Address roadmap coverage gaps, starting with: " + ", ".join(outstanding))
        else:
            recs.append("Review roadmap alignment to push coverage toward 100%.")
    if evolution_metrics["entries"] and evolution_metrics["novel_average"] < 1:
        recs.append("Increase experimentation with novel neurons to diversify network capabilities.")

    if operability_metrics.get("coverage", 0.0) < 100:
        recs.append(
            "Improve module operability coverage by resolving failed profile checks and missing validations."
        )

    domains = operability_metrics.get("domains", {})
    offline_cov = float(domains.get("offline-updater-readiness", 0.0)) if isinstance(domains, dict) else 0.0
    if offline_cov < 100:
        recs.append(
            "Raise offline updater readiness: keep imp-code-updater offline fallback intact and ensure at least one GGUF model is available in models/."
        )

    if not recs:
        recs.append("Systems are balanced; continue scheduled self-evolution cycles and monitoring.")
    return recs


def run_review() -> Dict[str, Any]:
    """Execute the general intelligence review and persist the results."""
    goals = _load_log("imp-goals.json", [])
    learning = _load_log("imp-learning-memory.json", [])
    roadmap = _load_log("imp-roadmap-progress.json", {})
    evolution = _load_log("imp-evolution-log.json", [])
    experiments = _load_log("imp-novel-neuron-experiments.json", [])
    operability = _load_log("imp-module-operability.json", [])

    goal_metrics = _goal_metrics(goals)
    learning_metrics = _learning_memory_metrics(learning)
    roadmap_metrics = _roadmap_metrics(roadmap)
    evolution_metrics = _evolution_metrics(evolution)
    operability_metrics = _operability_metrics(operability)

    entry = {
        "checked_at": _timestamp(),
        "goal_metrics": goal_metrics,
        "learning_metrics": learning_metrics,
        "roadmap_metrics": roadmap_metrics,
        "evolution_metrics": evolution_metrics,
        "operability_metrics": operability_metrics,
        "experiment_samples": experiments[-5:] if experiments else [],
    }
    entry["recommendations"] = _recommendations(
        goal_metrics,
        learning_metrics,
        roadmap_metrics,
        evolution_metrics,
        operability_metrics,
    )

    history = read_json(REVIEW_LOG, [])
    previous = history[-1] if history else None
    entry["trends"] = _trend_snapshot(previous, entry)
    entry["regression_flags"] = _regression_flags(previous, entry)
    history.append(entry)
    write_json(REVIEW_LOG, history)
    return entry


def _format_summary(entry: Dict[str, Any]) -> str:
    """Return a human readable summary for CLI use."""
    trends = entry.get("trends", {})
    lines = [f"General intelligence review @ {entry['checked_at']}"]
    lines.append(
        "Goals: {total} tracked, completion {rate}% (delta {delta:+.2f}%).".format(
            total=entry["goal_metrics"]["total"],
            rate=entry["goal_metrics"]["completion_rate"],
            delta=trends.get("goal_completion_delta", 0.0),
        )
    )
    lines.append(
        "Learning memory entries: {count} (recent {recent}) delta {delta:+d}.".format(
            count=entry["learning_metrics"]["entries"],
            recent=len(entry["learning_metrics"]["recent"]),
            delta=trends.get("learning_entries_delta", 0),
        )
    )
    lines.append(
        "Roadmap coverage: {coverage}% across {tracked} goals (delta {delta:+.2f}%).".format(
            coverage=entry["roadmap_metrics"]["coverage"],
            tracked=entry["roadmap_metrics"]["goals_tracked"],
            delta=trends.get("roadmap_coverage_delta", 0.0),
        )
    )
    lines.append(
        "Evolution snapshots: {entries} logged (delta {delta:+d}), novel avg {avg} (delta {novel:+.2f}).".format(
            entries=entry["evolution_metrics"]["entries"],
            delta=trends.get("evolution_entries_delta", 0),
            avg=entry["evolution_metrics"]["novel_average"],
            novel=trends.get("novel_average_delta", 0.0),
        )
    )
    lines.append(
        "Operability coverage: {coverage}% (delta {delta:+.2f}%), offline updater {offline}%.".format(
            coverage=entry.get("operability_metrics", {}).get("coverage", 0.0),
            delta=trends.get("operability_coverage_delta", 0.0),
            offline=entry.get("operability_metrics", {})
            .get("domains", {})
            .get("offline-updater-readiness", 0.0),
        )
    )
    lines.append("Recommendations:")
    for rec in entry["recommendations"]:
        lines.append(f"- {rec}")
    flags = entry.get("regression_flags", [])
    if flags:
        lines.append("Regression flags detected:")
        for flag in flags:
            lines.append(f"! {flag}")
    else:
        lines.append("No regressions detected in this cycle.")
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_review()
    print(_format_summary(result))
