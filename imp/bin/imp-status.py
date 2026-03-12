from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
REPO_ROOT = CURRENT_FILE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from imp.runtime import PID_FILE, START_STATE_FILE, read_json


def main() -> int:
    state = read_json(START_STATE_FILE, {})
    pids = read_json(PID_FILE, [])

    print("IMP status")
    print(f"  state file: {START_STATE_FILE}")
    print(f"  pid file: {PID_FILE}")

    if isinstance(state, dict) and state:
        print(f"  status: {state.get('status', 'unknown')}")
        print(f"  repo root: {state.get('repo_root', 'unknown')}")
        print(f"  imp root: {state.get('imp_root', 'unknown')}")
        print(f"  python: {state.get('python', 'unknown')}")
        print(f"  platform: {state.get('platform', 'unknown')}")
        print(f"  cwd: {state.get('cwd', 'unknown')}")
    else:
        print("  status: no startup state recorded")

    if pids:
        print("  processes:")
        for entry in pids:
            if isinstance(entry, dict):
                print(f"    - {entry.get('name', 'unknown')} pid={entry.get('pid', 'unknown')}")
            else:
                print(f"    - pid={entry}")
    else:
        print("  processes: no PID metadata recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
