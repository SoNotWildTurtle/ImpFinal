from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SH_SCRIPT = SCRIPT_DIR / "run-all-tests.sh"


def _parse_shell_script() -> list[str]:
    if not SH_SCRIPT.exists():
        raise FileNotFoundError(f"Missing {SH_SCRIPT}")
    tests: list[str] = []
    for raw in SH_SCRIPT.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("run_test ") and not line.startswith("python3 "):
            continue
        target = line.split(" ", 1)[1].strip().strip('"')
        target = target.replace("$SCRIPT_DIR/", "")
        if not target.endswith(".py"):
            continue
        tests.append(str(SCRIPT_DIR / target))
    return tests


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the IMP test suite.")
    parser.add_argument("--full", action="store_true", help="Run the full suite, including slow tests.")
    parser.add_argument("--fast", action="store_true", help="Force fast mode (skip slow tests).")
    parser.add_argument("--smoke", action="store_true", help="Run only the bootstrap smoke validation.")
    parser.add_argument(
        "--allow-self-modifying-tests",
        action="store_true",
        help="Run tests that may rewrite repository files.",
    )
    args = parser.parse_args()

    print("Running Full IMP System Test Suite...")
    if args.smoke:
        smoke = SCRIPT_DIR / "smoke.py"
        result = subprocess.run([sys.executable, str(smoke)])
        return result.returncode
    tests = _parse_shell_script()
    env = os.environ.copy()
    env.setdefault("PYTHONWARNINGS", "ignore::DeprecationWarning")
    fast_mode = args.fast or (platform.system() == "Windows" and not args.full)
    if fast_mode:
        env.setdefault("IMP_FAST_TESTS", "1")
        env.setdefault("IMP_DISABLE_LEDGER_RESTORE", "1")
        env.setdefault("IMP_SUPPRESS_SECRET_SCAN", "1")
    if not args.allow_self_modifying_tests:
        env.setdefault("IMP_SAFE_TESTS", "1")

    skip_fast = {
        "test-self-healer.py",
        "test-auto-heal.py",
        "test-chained-workflow.py",
        "test-3d-network.py",
        "test-chat-keepalive.py",
        "test-chat-verify.py",
        "test-auto-heal-script.py",
    }
    skip_self_modifying = {
        "test-code-updater.py",
        "test-self-healer.py",
        "test-auto-heal.py",
        "test-backup-restore.py",
        "test-chained-workflow.py",
        "test-auto-heal-script.py",
    }

    for test in tests:
        name = Path(test).name
        if env.get("IMP_FAST_TESTS") == "1" and name in skip_fast:
            print(f"Skipping {test} (IMP_FAST_TESTS=1)")
            continue
        if env.get("IMP_SAFE_TESTS") == "1" and name in skip_self_modifying:
            print(f"Skipping {test} (IMP_SAFE_TESTS=1)")
            continue
        print(f"Running {test}")
        result = subprocess.run([sys.executable, test], env=env)
        if result.returncode != 0:
            print(f"Test failed: {test}")
            return result.returncode
    print("All Tests Completed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
