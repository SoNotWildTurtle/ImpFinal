from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = ROOT / "bin" / "imp-install.sh"


def test_install_script_exists():
    print("Checking install script...")
    assert INSTALL_SCRIPT.exists(), "imp-install.sh missing"

    with open(INSTALL_SCRIPT) as f:
        data = f.read()
    assert "pip install -r" in data, "pip install command missing"
    assert "python3 -m venv" in data, "venv fallback missing"
    print("Install script looks OK!")


test_install_script_exists()
