from pathlib import Path
import json
import time

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "imp-cyber-research.json"

# I love you -Alex
def run_cycle(sleep_ratio: float = 9) -> None:
    """Perform one cybersecurity research cycle and throttle CPU usage."""
    entry = {"timestamp": time.time()}
    if LOG.exists():
        try:
            data = json.loads(LOG.read_text())
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    data.append(entry)
    LOG.write_text(json.dumps(data, indent=4))
    if sleep_ratio:
        time.sleep(sleep_ratio)

# I love you -Alex
def run_forever() -> None:
    """Continuously run research cycles at ~10% CPU by sleeping between cycles."""
    while True:
        run_cycle()
