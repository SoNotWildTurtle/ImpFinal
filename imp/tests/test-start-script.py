from pathlib import Path


def test_start_script_delegates_to_python_supervisor():
    root = Path(__file__).resolve().parents[1]
    script_text = (root / "bin" / "imp-start.sh").read_text(encoding="utf-8")
    assert 'exec "$PYTHON_BIN"' in script_text
    assert "imp-start.py" in script_text
