import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_script(path: Path, timeout_seconds: int = 30) -> None:
    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"{path.name} failed with exit code {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def test_vulnerability_scanner() -> None:
    print("Running Vulnerability Scanner...")
    _run_script(ROOT / "security" / "imp-vulnerability-scanner.py")
    print("Vulnerability Scanner Test Passed!")


def test_poison_detector() -> None:
    print("Running Poison Detector...")
    _run_script(ROOT / "security" / "imp-poison-detector.py")
    print("Poison Detector Test Passed!")


if __name__ == "__main__":
    test_vulnerability_scanner()
    test_poison_detector()
