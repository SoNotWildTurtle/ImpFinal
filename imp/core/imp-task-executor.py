from pathlib import Path
from typing import Optional
import importlib.util

spec_utils = importlib.util.spec_from_file_location(
    "imp_utils", Path(__file__).resolve().parent / "imp_utils.py"
)
imp_utils = importlib.util.module_from_spec(spec_utils)
spec_utils.loader.exec_module(imp_utils)

spec = importlib.util.spec_from_file_location(
    "imp_mood_manager", (Path(__file__).resolve().parent / "imp-mood-manager.py")
)
imp_mood_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp_mood_manager)

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

ROOT = Path(__file__).resolve().parents[1]
GOALS_FILE = ROOT / "logs" / "imp-goals.json"


def get_goals() -> list:
    """Load all goals from disk."""
    return imp_utils.read_json(GOALS_FILE, [])

def get_pending_goals(term: Optional[str] = None):
    """Return pending goals optionally filtered by term."""
    goals = get_goals()
    pending = [g for g in goals if g.get("status") == "pending"]
    if term:
        pending = [g for g in pending if g.get("term") == term]
    pending.sort(key=lambda g: PRIORITY_ORDER.get(g.get("priority", "medium"), 1))
    return pending


def execute_goals(term: Optional[str] = None):
    """Execute pending goals sorted by priority."""
    goals = get_goals()
    pending = [g for g in goals if g.get("status") == "pending"]
    if term:
        pending = [g for g in pending if g.get("term") == term]
    pending.sort(key=lambda g: PRIORITY_ORDER.get(g.get("priority", "medium"), 1))

    for goal in pending:
        print(f"Executing goal: {goal['goal']}")
        goal["status"] = "completed"
        imp_mood_manager.update_mood("goal_completed")

    imp_utils.write_json(GOALS_FILE, goals)


if __name__ == "__main__":
    choice = input("Execute short-term or long-term goals? [s/l/all]: ").strip().lower()
    if choice.startswith("s"):
        execute_goals("short-term")
    elif choice.startswith("l"):
        execute_goals("long-term")
    else:
        execute_goals()
