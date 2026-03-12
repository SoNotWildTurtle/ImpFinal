from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_root_command_wrappers_exist():
    for relative in [
        "bin/imp-install.sh",
        "bin/imp-start.sh",
        "bin/imp-stop.sh",
        "bin/imp-operator-dashboard.sh",
        "bin/imp-chat-keepalive.sh",
        "bin/imp-control-hub.sh",
        "bin/imp-defend.sh",
        "bin/imp-incident-report.sh",
        "bin/imp-network-monitor.sh",
        "bin/imp-nn-menu.sh",
        "bin/imp-processing-forecast.sh",
        "bin/imp-processing-report.sh",
        "bin/imp-verify-chat.sh",
        "bin/imp-readiness.sh",
        "bin/imp-self-heal.sh",
        "bin/imp-status.sh",
        "bin/imp-success-plan.sh",
        "bin/imp-voice-menu.sh",
        "bin/imp-zero-trust.sh",
        "tests/run-all-tests.sh",
        "tests/run-all-tests.py",
    ]:
        path = REPO_ROOT / relative
        assert path.exists(), f"Missing documented wrapper: {relative}"
        assert path.stat().st_size > 0, f"Wrapper is empty: {relative}"


def test_python_module_wrappers_import():
    sys.path.insert(0, str(REPO_ROOT))
    importlib.import_module("imp")
    importlib.import_module("imp.core.imp_execute")
    importlib.import_module("imp.core.imp_operator_dashboard")
    importlib.import_module("imp.bin.imp_start")
    importlib.import_module("imp.bin.imp_stop")


def test_root_python_test_wrapper_executes_help():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tests" / "run-all-tests.py"), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Run the IMP test suite." in result.stdout
