import json
import os
import signal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PID_FILE = ROOT / "logs" / "imp-pids.json"


def _extract_pid(entry):
    if isinstance(entry, int):
        return entry
    if isinstance(entry, dict):
        return entry.get("pid")
    return None


def main() -> int:
    if PID_FILE.exists():
        with open(PID_FILE, "r", encoding="utf-8") as f:
            try:
                pids = json.load(f)
            except Exception:
                pids = []
        stopped = 0
        for entry in pids:
            pid = _extract_pid(entry)
            if not isinstance(pid, int):
                continue
            try:
                os.kill(pid, signal.SIGTERM)
                stopped += 1
            except OSError:
                pass
        PID_FILE.unlink(missing_ok=True)
        print(f"IMP AI stop signal sent to {stopped} process(es).")
        return 0

    print("No running IMP processes found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
