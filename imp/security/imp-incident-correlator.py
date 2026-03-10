"""Aggregate security signals into incident reports."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs"
OUTPUT_FILE = LOG_DIR / "imp-incident-report.json"


@dataclass
class Incident:
    category: str
    description: str
    severity: str
    source: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "source": self.source,
        }


def _load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return fallback
    except json.JSONDecodeError:
        return fallback


def _normalize_threats(data: Mapping[str, Any]) -> Iterable[Incident]:
    for key, value in data.items():
        yield Incident(
            category="threat-monitor",
            description=f"{key}: {value}",
            severity="high",
            source="imp-threat-monitor",
        )


def _normalize_network(diff_entries: Iterable[Mapping[str, Any]]) -> Iterable[Incident]:
    for entry in diff_entries:
        event = entry.get("event") or entry.get("status") or "change"
        details = []
        if host := entry.get("host"):
            details.append(f"host={host}")
        if port := entry.get("port"):
            details.append(f"port={port}")
        if reason := entry.get("reason"):
            details.append(str(reason))
        detail = ", ".join(details) if details else "no additional context"
        severity = "medium" if event in {"new_host", "new_connection"} else "low"
        yield Incident(
            category="network",
            description=f"{event}: {detail}",
            severity=severity,
            source="imp-network-discovery",
        )


def _normalize_process(findings: Iterable[Mapping[str, Any]]) -> Iterable[Incident]:
    for entry in findings:
        name = entry.get("process") or entry.get("command") or "unknown-process"
        reason = entry.get("reason") or entry.get("detail") or "flagged by process audit"
        severity = str(entry.get("severity") or "medium")
        yield Incident(
            category="process",
            description=f"{name}: {reason}",
            severity=severity,
            source="imp-process-auditor",
        )


def correlate_incidents(log_dir: Optional[Path] = None) -> Dict[str, Any]:
    base_dir = log_dir or LOG_DIR

    threat_data = _load_json(base_dir / "imp-threat-log.json", {})
    network_diff = _load_json(base_dir / "imp-network-diff.json", [])
    process_audit = _load_json(base_dir / "imp-process-audit.json", [])

    incidents: List[Incident] = []
    if isinstance(threat_data, Mapping):
        incidents.extend(_normalize_threats(threat_data))
    if isinstance(network_diff, list):
        incidents.extend(
            _normalize_network(entry for entry in network_diff if isinstance(entry, Mapping))
        )
    if isinstance(process_audit, list):
        incidents.extend(
            _normalize_process(entry for entry in process_audit if isinstance(entry, Mapping))
        )

    severity_counts = Counter(incident.severity for incident in incidents)
    category_counts = Counter(incident.category for incident in incidents)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_incidents": len(incidents),
        "by_severity": dict(severity_counts),
        "by_category": dict(category_counts),
        "incidents": [incident.to_dict() for incident in incidents],
    }

    output_path = base_dir / OUTPUT_FILE.name
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    return report


def latest_report(log_dir: Optional[Path] = None) -> Dict[str, Any]:
    base_dir = log_dir or LOG_DIR
    return _load_json(base_dir / OUTPUT_FILE.name, {})


def main() -> None:
    report = correlate_incidents()
    summary = report.get("by_category", {})
    print("IMP Incident Report generated")
    print(f"Total incidents: {report.get('total_incidents', 0)}")
    if summary:
        print("By category:")
        for category, count in sorted(summary.items()):
            print(f"  - {category}: {count}")


if __name__ == "__main__":
    main()
