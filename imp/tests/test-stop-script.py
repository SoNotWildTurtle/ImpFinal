from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
STOP = ROOT / 'bin' / 'imp-stop.sh'


def test_stop_script_contains_kill():
    assert STOP.exists(), 'imp-stop.sh missing'
    assert os.access(STOP, os.X_OK), 'imp-stop.sh not executable'
    text = STOP.read_text()
    assert 'pkill -f imp-execute.py' in text
