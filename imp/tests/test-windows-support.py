from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START_PY = ROOT / "bin" / "imp-start.py"
STOP_PY = ROOT / "bin" / "imp-stop.py"
PS_START = ROOT.parent / "imp-start.ps1"


def test_start_script():
    data = START_PY.read_text(encoding="utf-8")
    assert "freeze_support" in data
    assert "write_json" in data


def test_stop_script():
    data = STOP_PY.read_text(encoding="utf-8")
    assert "os.kill" in data
    assert "_extract_pid" in data


def test_powershell_keepalive():
    data = PS_START.read_text(encoding="utf-8").lower()
    assert "imp-start.py" in data
    assert "ensure-openssh" in data
    assert "convertto-json" in data
    assert "imp_remote_dir" in data
