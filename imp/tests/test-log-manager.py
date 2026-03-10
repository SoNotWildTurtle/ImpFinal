from pathlib import Path
import json
import sys
import importlib.util

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

spec = importlib.util.spec_from_file_location(
    "log_manager", Path(__file__).resolve().parents[1] / "logs" / "imp-log-manager.py"
)
log_manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(log_manager)

ensure_logs = log_manager.ensure_logs
clean_logs = log_manager.clean_logs
LOG_FILES = log_manager.LOG_FILES


def test_ensure_and_clean_logs():
    ensure_logs()
    for path in LOG_FILES.values():
        assert path.exists(), f"missing log file {path}"
    clean_logs("activity")
    data = json.loads(LOG_FILES["activity"].read_text())
    assert data == []
