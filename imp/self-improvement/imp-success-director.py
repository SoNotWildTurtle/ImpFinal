"""Generate a success plan by combining readiness reviews with actionable goals."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
IMP_DIR = ROOT / "imp"
LOG_DIR = IMP_DIR / "logs"
PLAN_LOG = LOG_DIR / "imp-success-plan.json"


def _load(name: str, path: Path):
    """Load a module from a given path."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_utils = _load("imp_utils", IMP_DIR / "core" / "imp_utils.py")
read_json = _utils.read_json
write_json = _utils.write_json

goal_manager = _load("imp_goal_manager", IMP_DIR / "core" / "imp-goal-manager.py")
reviewer = _load(
    "imp_general_intelligence_review",
    IMP_DIR / "self-improvement" / "imp-general-intelligence-review.py",
)
context_engine = _load(
    "imp_context_engine",
    IMP_DIR / "self-improvement" / "imp-context-engine.py",
)


def _timestamp() -> str:
    """Return a UTC timestamp."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _pending_goal_texts() -> List[str]:
    """Return goal strings already tracked to avoid duplicates."""
    return [goal.get("goal", "") for goal in goal_manager.get_existing_goals()]


def _add_goal(action: Dict[str, Any]) -> bool:
    """Persist the provided action as a new goal if it is novel."""
    if action.get("goal") in _pending_goal_texts():
        return False

    goals = goal_manager.get_existing_goals()
    goals.append(
        {
            "id": goal_manager._goal_id(),
            "goal": action["goal"],
            "term": action["term"],
            "priority": action["priority"],
            "status": "pending",
            "created_at": goal_manager._timestamp(),
            "category": action["category"] or goal_manager.DEFAULT_CATEGORY,
        }
    )
    goal_manager.write_json(goal_manager.GOALS_FILE, goals)
    return True


def _plan_from_metrics(review_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Translate readiness metrics into concrete follow-up actions."""
    metrics = review_entry
    actions: List[Dict[str, Any]] = []

    goal_metrics = metrics.get("goal_metrics", {})
    completion_rate = goal_metrics.get("completion_rate", 0)
    if completion_rate < 80:
        severity = "high" if completion_rate < 50 else "medium"
        actions.append(
            {
                "goal": "Review pending goals and close blockers to lift completion above 80%",
                "priority": severity,
                "category": "self-management",
                "term": "short-term",
                "reason": f"Goal completion currently at {completion_rate}%",
            }
        )

    learning_metrics = metrics.get("learning_metrics", {})
    entries = learning_metrics.get("entries", 0)
    if entries < 10:
        actions.append(
            {
                "goal": "Capture new learning memory entries after major experiments",
                "priority": "medium",
                "category": "reflection",
                "term": "short-term",
                "reason": f"Learning memory holds only {entries} insights",
            }
        )

    roadmap_metrics = metrics.get("roadmap_metrics", {})
    coverage = roadmap_metrics.get("coverage", 0)
    if coverage < 100:
        gaps = roadmap_metrics.get("gaps", [])
        target = ", ".join(module for _, module in gaps[:2]) if gaps else "roadmap goals"
        actions.append(
            {
                "goal": f"Address roadmap gaps by implementing {target}",
                "priority": "medium",
                "category": "roadmap",
                "term": "long-term",
                "reason": f"Roadmap coverage at {coverage}%",
            }
        )

    evolution_metrics = metrics.get("evolution_metrics", {})
    novel_avg = evolution_metrics.get("novel_average", 0.0)
    entries_logged = evolution_metrics.get("entries", 0)
    if entries_logged < 3 or novel_avg < 1:
        actions.append(
            {
                "goal": "Schedule additional novel neuron experiments to diversify evolution history",
                "priority": "medium",
                "category": "neural-evolution",
                "term": "long-term",
                "reason": f"Evolution log has {entries_logged} entries with average novel score {novel_avg}",
            }
        )

    operability_metrics = metrics.get("operability_metrics", {})
    operability_coverage = operability_metrics.get("coverage", 100.0)
    if operability_coverage < 100:
        actions.append(
            {
                "goal": "Resolve failed operability profile checks to restore full module readiness",
                "priority": "high",
                "category": "operability",
                "term": "short-term",
                "reason": f"Operability coverage currently at {operability_coverage}%",
            }
        )

    domains = operability_metrics.get("domains", {})
    offline_cov = domains.get("offline-updater-readiness", 100.0) if isinstance(domains, dict) else 100.0
    if offline_cov < 100:
        actions.append(
            {
                "goal": "Restore offline updater readiness by validating GGUF assets and fallback generation path",
                "priority": "high",
                "category": "operability",
                "term": "short-term",
                "reason": f"Offline updater readiness at {offline_cov}%",
            }
        )

    if not actions:
        actions.append(
            {
                "goal": "Continue routine self-analysis cycles to maintain current readiness",
                "priority": "low",
                "category": "self-management",
                "term": "long-term",
                "reason": "All monitored metrics within target ranges",
            }
        )

    return actions


def build_success_plan(add_goals: bool = True) -> Dict[str, Any]:
    """Run a readiness review and persist an actionable success plan."""
    context_bundle = context_engine.build_context_bundle()
    review_entry = reviewer.run_review()
    actions = _plan_from_metrics(review_entry)
    plan_entry = {
        "prepared_at": _timestamp(),
        "review_timestamp": review_entry.get("checked_at"),
        "context_timestamp": context_bundle.get("created_at"),
        "context_sources": context_bundle.get("source_count", 0),
        "context_missing_sources": context_bundle.get("missing_sources", []),
        "actions": actions,
    }

    history = read_json(PLAN_LOG, [])
    history.append(plan_entry)
    write_json(PLAN_LOG, history)

    added: List[str] = []
    if add_goals:
        for action in actions:
            if _add_goal(action):
                added.append(action["goal"])
    return {"plan": plan_entry, "goals_added": added}


def _format_summary(result: Dict[str, Any]) -> str:
    """Return a human-readable representation for CLI usage."""
    lines = [
        f"Success plan prepared @ {result['plan']['prepared_at']} (review {result['plan']['review_timestamp']})",
    ]
    lines.append("Actions:")
    for action in result["plan"]["actions"]:
        lines.append(
            f"- {action['goal']} [{action['priority']}, {action['term']}] -- {action['reason']}"
        )
    if result["goals_added"]:
        lines.append("Goals added:")
        for goal in result["goals_added"]:
            lines.append(f"  * {goal}")
    else:
        lines.append("No new goals were added (already tracked).")
    return "\n".join(lines)


if __name__ == "__main__":
    print(_format_summary(build_success_plan()))
