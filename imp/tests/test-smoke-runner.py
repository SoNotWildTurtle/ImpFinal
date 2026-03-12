from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_smoke_runner_executes():
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tests" / "smoke.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Smoke validation passed." in result.stdout
