from pathlib import Path
import json
import os
import py_compile
import time

ROOT = Path(__file__).resolve().parents[1]
BUG_LOG = ROOT / "logs" / "imp-bug-report.json"
SKIP_PARTS = {
    "__pycache__",
    ".venv",
    "logs",
    "imp-ledger-blobs",
    "imp-update-patches",
}


def _resolve_pause(pause: float | None) -> float:
    """Return the pause to use between batches.

    ``pause`` may be provided explicitly or via the ``IMP_BUG_HUNTER_PAUSE``
    environment variable.  Negative or invalid values are coerced to zero so
    automated environments are not forced to wait between batches.
    """

    if pause is None:
        env_value = os.environ.get("IMP_BUG_HUNTER_PAUSE")
        if env_value is not None:
            try:
                pause = float(env_value)
            except ValueError:
                pause = 0.0
        else:
            pause = 0.0
    return max(0.0, float(pause))


def scan_repository(batch_size: int = 50, pause: float | None = None) -> None:
    """Compile Python files in manageable batches to detect syntax errors."""

    pause_duration = _resolve_pause(pause)
    files = []
    for path in ROOT.rglob("*.py"):
        parts = set(path.parts)
        if parts.intersection(SKIP_PARTS):
            continue
        files.append(path)
    issues = []
    for i in range(0, len(files), batch_size):
        for path in files[i : i + batch_size]:
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as exc:
                issues.append({"file": str(path.relative_to(ROOT)), "error": str(exc)})
        if pause_duration:
            time.sleep(pause_duration)
    with open(BUG_LOG, 'w') as f:
        json.dump(issues, f, indent=4)
    print(f"Bug hunt complete. {len(issues)} issues logged in batches of {batch_size}.")


if __name__ == "__main__":
    scan_repository()
