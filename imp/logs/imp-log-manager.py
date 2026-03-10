import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_FILES = {
    "activity": (ROOT / "logs" / "imp-activity-log.json", []),
    "security": (ROOT / "logs" / "imp-security-log.json", []),
    "updates": (ROOT / "logs" / "imp-update-log.json", []),
    "decisions": (ROOT / "logs" / "imp-decision-log.json", []),
    "performance": (ROOT / "logs" / "imp-performance.json", []),
    "integrity": (ROOT / "logs" / "imp-integrity-log.json", []),
    "mood": (ROOT / "logs" / "imp-mood.json", []),
    "tone": (ROOT / "logs" / "imp-tone-log.json", []),
    "autonomy": (ROOT / "logs" / "imp-autonomy-log.json", []),
    "processing_report": (ROOT / "logs" / "imp-processing-report.json", []),
    "processing_forecast": (ROOT / "logs" / "imp-processing-forecast.json", []),
    "processing_resilience": (ROOT / "logs" / "imp-processing-resilience.json", []),
    "session_guard": (ROOT / "logs" / "imp-session-guard.json", []),
    "incident_report": (ROOT / "logs" / "imp-incident-report.json", {}),
    "control_hub": (ROOT / "logs" / "imp-control-hub.json", []),
    "control_queue": (ROOT / "logs" / "imp-control-queue.json", []),
}

def ensure_logs():
    """Create log files if they don't exist."""
    for path, default in LOG_FILES.values():
        if not path.exists():
            if path.suffix == ".json":
                path.write_text(json.dumps(default, indent=2), encoding="utf-8")
            else:
                path.touch()

def review_logs(log_type):
    if log_type not in LOG_FILES:
        print("Invalid log type.")
        return

    path, _ = LOG_FILES[log_type]
    with open(path, "r") as f:
        logs = json.load(f)
        for entry in logs:
            print(json.dumps(entry, indent=4))

def clean_logs(log_type):
    if log_type not in LOG_FILES:
        print("Invalid log type.")
        return

    path, default = LOG_FILES[log_type]
    with open(path, "w") as f:
        json.dump(default, f, indent=4)

    print(f"{log_type} logs have been cleared.")

if __name__ == "__main__":
    ensure_logs()
    if len(sys.argv) == 3 and sys.argv[1] in {"review", "clean"}:
        if sys.argv[1] == "review":
            review_logs(sys.argv[2])
        else:
            clean_logs(sys.argv[2])

