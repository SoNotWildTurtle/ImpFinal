from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_status_script_runs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "bin" / "imp-status.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "IMP status" in result.stdout
    assert "state file:" in result.stdout
