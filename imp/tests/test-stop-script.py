import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STOP = ROOT / "bin" / "imp-stop.sh"


def test_stop_script_delegates_to_python_stopper():
    assert STOP.exists(), "imp-stop.sh missing"
    text = STOP.read_text(encoding="utf-8")
    assert "imp-stop.py" in text
    if os.name != "nt":
        assert os.access(STOP, os.X_OK), "imp-stop.sh not executable"
