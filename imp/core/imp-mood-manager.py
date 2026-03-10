import importlib.util
from pathlib import Path

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
utils = _load("imp_utils", ROOT / "core" / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json

MOOD_FILE = ROOT / "logs" / "imp-mood.json"
BASELINE = 0.1  # Wah should remain slightly positive

EVENT_DELTAS = {
    "goal_completed": 0.05,
    "goal_failed": -0.1,
    "security_alert": -0.2,
}


def load_mood() -> float:
    data = read_json(MOOD_FILE, {"mood": BASELINE})
    return float(data.get("mood", BASELINE))


def save_mood(value: float) -> None:
    write_json(MOOD_FILE, {"mood": value})


def adjust_mood(delta: float) -> float:
    mood = load_mood()
    mood = max(-1.0, min(1.0, mood + delta))
    save_mood(mood)
    return mood


# Wah should always return toward a slightly positive mood over time
# This function nudges the stored mood toward BASELINE on each call
def decay_toward_baseline() -> float:
    mood = load_mood()
    mood += (BASELINE - mood) * 0.1
    save_mood(mood)
    return mood


def update_mood(event: str) -> float:
    """Adjust mood based on an event type."""
    if event in EVENT_DELTAS:
        return adjust_mood(EVENT_DELTAS[event])
    return decay_toward_baseline()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage IMP mood state")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--get", action="store_true", help="Print current mood")
    group.add_argument("--adjust", type=float, help="Adjust mood by delta")
    group.add_argument("--decay", action="store_true", help="Decay toward baseline")
    group.add_argument("--event", type=str, help="Update mood based on event")
    args = parser.parse_args()

    if args.get:
        print(f"Current mood: {load_mood():.2f}")
    elif args.adjust is not None:
        print(f"New mood: {adjust_mood(args.adjust):.2f}")
    elif args.event:
        print(f"Mood after event: {update_mood(args.event):.2f}")
    else:  # default action is decay toward baseline
        if not args.decay:
            # if no option provided, treat as --decay for backward compatibility
            args.decay = True
        if args.decay:
            print(f"Mood after decay: {decay_toward_baseline():.2f}")
