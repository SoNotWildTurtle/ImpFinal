from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    print("IMP smoke validation")

    for relative in [
        "README.md",
        "SETUP.md",
        "imp-start.ps1",
        "imp-start-wrapper.ps1",
        "bin/imp-install.sh",
        "bin/imp-start.sh",
        "bin/imp-stop.sh",
        "bin/imp-status.sh",
        "bin/imp-operator-dashboard.sh",
        "tests/run-all-tests.py",
    ]:
        _check((REPO_ROOT / relative).exists(), f"Missing required path: {relative}")

    sys.path.insert(0, str(REPO_ROOT))
    importlib.import_module("imp")
    importlib.import_module("imp.runtime")
    importlib.import_module("imp.bin.imp_start")
    importlib.import_module("imp.bin.imp_stop")
    importlib.import_module("imp.bin.imp_status")
    importlib.import_module("imp.core.imp_execute")
    importlib.import_module("imp.core.imp_operator_dashboard")

    checks = [
        [sys.executable, str(REPO_ROOT / "tests" / "run-all-tests.py"), "--help"],
        [sys.executable, str(ROOT / "core" / "imp-operator-dashboard.py"), "--list"],
        [sys.executable, str(ROOT / "core" / "imp-speech-to-text.py"), "--check"],
        [sys.executable, str(ROOT / "bin" / "imp-status.py")],
    ]
    for command in checks:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        _check(result.returncode == 0, f"Command failed: {' '.join(command)}")

    print("Smoke validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
