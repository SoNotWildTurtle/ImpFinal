"""Maintain structured learning insights derived from past decisions."""

import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
utils = _load("imp_utils", ROOT / "core" / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json
LEARNING_FILE = ROOT / "logs" / "imp-learning-memory.json"
DECISIONS_FILE = ROOT / "logs" / "imp-decision-log.json"

CATEGORY_KEYWORDS: Dict[str, Sequence[str]] = {
    "security": ("breach", "unauthorized", "malware", "intrusion", "firewall"),
    "performance": ("latency", "throughput", "cpu", "efficiency", "memory"),
    "reliability": ("redundancy", "failover", "backup", "resilience"),
    "compliance": ("audit", "policy", "compliance", "regulation"),
}


def _timestamp() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _entry_key(decision: str, reason: str) -> str:
    return f"{decision.strip().lower()}::{reason.strip().lower()}"


def _categorise(decision: str, reason: str) -> List[str]:
    combined = f"{decision} {reason}".lower()
    categories = [
        name
        for name, keywords in CATEGORY_KEYWORDS.items()
        if any(keyword in combined for keyword in keywords)
    ]
    return categories or ["general"]


def _build_learning(decision_entry: Dict[str, object]) -> Dict[str, object]:
    decision_text = (
        str(decision_entry.get("decision") or decision_entry.get("goal") or "unspecified decision")
    )
    reason = str(decision_entry.get("reason") or "No reason captured")
    predicted = str(
        decision_entry.get("predicted_outcome")
        or decision_entry.get("outcome")
        or "unknown outcome"
    )
    plan = decision_entry.get("plan") if isinstance(decision_entry.get("plan"), list) else []
    timestamp = str(decision_entry.get("timestamp") or _timestamp())
    status = str(decision_entry.get("status") or "pending")

    categories = _categorise(decision_text, reason)
    insight = f"{decision_text} because {reason}. Expected outcome: {predicted}."

    return {
        "timestamp": timestamp,
        "goal": str(decision_entry.get("goal") or decision_text),
        "decision": decision_text,
        "reason": reason,
        "predicted_outcome": predicted,
        "plan": plan,
        "categories": categories,
        "insight": insight,
        "status": status,
    }


def summarise_categories(entries: List[Dict[str, object]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entry in entries:
        for category in entry.get("categories", []):
            counts[category] = counts.get(category, 0) + 1
    return counts


def store_learnings():
    past_decisions = read_json(DECISIONS_FILE, [])

    if not past_decisions:
        print("[+] No new knowledge to store.")
        return

    learning_memory = read_json(LEARNING_FILE, [])
    existing_keys = {
        _entry_key(
            str(entry.get("decision") or entry.get("goal") or ""),
            str(entry.get("reason") or ""),
        )
        for entry in learning_memory
    }

    new_entries: List[Dict[str, object]] = []

    for decision in past_decisions:
        learning = _build_learning(decision)
        key = _entry_key(learning["decision"], learning["reason"])
        if key in existing_keys:
            continue
        existing_keys.add(key)
        learning_memory.append(learning)
        new_entries.append(learning)

    write_json(LEARNING_FILE, learning_memory)

    if not new_entries:
        print("[+] No new knowledge to store.")
        return

    category_summary = summarise_categories(new_entries)
    print(f"[+] IMP has updated its knowledge base with {len(new_entries)} insights.")
    if category_summary:
        print(f"[+] Latest learning distribution: {category_summary}")


def _sorted_entries(entries: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Return entries sorted newest-first by timestamp.

    Falls back to reversing the input when timestamps cannot be compared so
    recently appended learnings remain near the start of the list.
    """

    try:
        return sorted(
            entries,
            key=lambda item: item.get("timestamp", ""),
            reverse=True,
        )
    except TypeError:
        return list(entries)[::-1]


def get_recent_learnings(limit: int = 5) -> List[Dict[str, object]]:
    memory = read_json(LEARNING_FILE, [])
    return _sorted_entries(memory)[:limit]


def filter_learnings(
    categories: Sequence[str] | str | None = None,
    *,
    status: str | None = None,
    limit: int | None = None,
) -> List[Dict[str, object]]:
    """Return learnings filtered by category and/or status."""

    memory = read_json(LEARNING_FILE, [])
    if not memory:
        return []

    if isinstance(categories, str):
        categories = [categories]

    category_set = {category.lower() for category in categories} if categories else set()
    status_value = status.lower() if status else None

    filtered: List[Dict[str, object]] = []
    for entry in memory:
        entry_categories = {
            str(category).lower() for category in entry.get("categories", [])
        }
        if category_set and not (entry_categories & category_set):
            continue
        if status_value is not None and str(entry.get("status", "")).lower() != status_value:
            continue
        filtered.append(entry)

    sorted_filtered = _sorted_entries(filtered)
    if limit is not None:
        return sorted_filtered[:limit]
    return sorted_filtered


if __name__ == "__main__":
    store_learnings()
