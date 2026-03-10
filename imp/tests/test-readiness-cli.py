import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readiness_cli_runs():
    result = subprocess.run(
        ["bash", str(ROOT / "bin" / "imp-readiness.sh")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "General intelligence review" in result.stdout


if __name__ == "__main__":
    test_readiness_cli_runs()
