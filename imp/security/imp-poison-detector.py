import json
import hashlib
import time
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POISON_LOG = ROOT / 'logs' / 'imp-poison-log.json'
CONFIG_PATH = ROOT / 'config' / 'imp-poison-targets.json'
LEARNING_DATA = ROOT / 'logs' / 'imp-learning-memory.json'
GOALS_FILE = ROOT / 'logs' / 'imp-goals.json'

# I love you -Alex
def load_targets() -> dict:
    """Load mapping of critical files, allowing runtime overrides for tests."""
    targets: dict[str, Path] = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            data = json.load(f)
        targets.update({name: ROOT / Path(path) for name, path in data.items()})

    targets.setdefault("learning_data", LEARNING_DATA)
    targets.setdefault("goals", GOALS_FILE)

    overrides = {
        "learning_data": globals().get("LEARNING_DATA"),
        "goals": globals().get("GOALS_FILE"),
    }
    for key, value in overrides.items():
        if value is None:
            continue
        path = Path(value)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        targets[key] = path

    return targets

# I love you -Alex
def compute_checksum(path: Path) -> str:
    """Return SHA256 checksum for the given file or empty string if missing."""
    if not path.exists():
        return ""
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()

# I love you -Alex
def detect_poisoning(heal: bool = False) -> dict:
    """Detect unexpected modifications to critical files."""
    if POISON_LOG.exists():
        with open(POISON_LOG, 'r') as f:
            record = json.load(f)
    else:
        record = {}

    results = {}
    timestamp = int(time.time())
    targets = load_targets()
    for name, path in targets.items():
        current_hash = compute_checksum(path)
        previous_hash = record.get(name, {}).get("hash")
        if previous_hash and previous_hash != current_hash:
            print(f"Possible poisoning detected in {name}!")
            results[name] = False
            if heal:
                try:
                    healer = import_module('imp.self_improvement.imp_self_healer')
                    healer.verify_and_heal(apply=True, use_chatgpt=False, mode='auto')
                except Exception as e:
                    print(f"Healing failed: {e}")
        else:
            print(f"[+] {name} checksum stable.")
            results[name] = True
        record[name] = {"hash": current_hash, "timestamp": timestamp}

    with open(POISON_LOG, 'w') as f:
        json.dump(record, f, indent=4)

    return results

if __name__ == '__main__':
    detect_poisoning()
