import importlib.util
import sys
from pathlib import Path


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


REPO_ROOT = Path(__file__).resolve().parents[2]
incident = _load(
    "imp_incident_correlator",
    REPO_ROOT / "imp" / "security" / "imp-incident-correlator.py",
)


def test_correlate_incidents_creates_report(tmp_path: Path):
    logs = tmp_path
    (logs / "imp-threat-log.json").write_text('{"Malware": "Detected"}')
    (logs / "imp-network-diff.json").write_text('[{"event": "new_host", "host": "10.0.0.8"}]')
    (logs / "imp-process-audit.json").write_text('[{"process": "nc", "reason": "suspicious", "severity": "high"}]')

    report = incident.correlate_incidents(logs)

    assert report["total_incidents"] == 3
    assert report["by_category"]["threat-monitor"] == 1
    assert any(entry["severity"] == "high" for entry in report["incidents"])

    report_file = logs / "imp-incident-report.json"
    assert report_file.exists()
    saved = incident.latest_report(logs)
    assert saved["total_incidents"] == 3
