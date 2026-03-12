from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = ROOT / "bin" / "imp-install.sh"


def test_install_script_exists():
    assert INSTALL_SCRIPT.exists(), "imp-install.sh missing"
    data = INSTALL_SCRIPT.read_text(encoding="utf-8")
    assert "pip install -r" in data, "pip install command missing"
    assert "-m venv" in data, "venv fallback missing"
