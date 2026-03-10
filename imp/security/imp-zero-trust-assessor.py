"""Zero-trust posture assessment for IMP.

This module inspects key configuration files and runtime logs to verify that
critical defensive controls remain enabled.  It surfaces actionable issues as
well as softer advisories so operators can close any remaining gaps before
remote execution or self-modification takes place.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = REPO_ROOT / "config"
LOG_ROOT = REPO_ROOT / "logs"


@dataclass
class Assessment:
    """Structured output for zero-trust checks."""

    issues: List[str] = field(default_factory=list)
    advisories: List[str] = field(default_factory=list)

    def status(self) -> str:
        if self.issues:
            return "attention"
        if self.advisories:
            return "advisory"
        return "pass"

    def as_dict(self) -> Dict[str, Iterable[str]]:
        return {
            "status": self.status(),
            "issues": list(self.issues),
            "advisories": list(self.advisories),
        }


def _read_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        # Treat malformed files as an issue the caller can flag.
        return default


def collect_posture(base_path: Optional[Path] = None) -> Dict[str, object]:
    """Load configuration/log information needed for a zero-trust review."""

    base = base_path if base_path is not None else REPO_ROOT
    config_root = base / "config"
    log_root = base / "logs"

    processing_security = _read_json(
        config_root / "imp-processing-security.json", {}
    )
    session_security = _read_json(
        config_root / "imp-session-security.json", {}
    )
    intranet = _read_json(config_root / "imp-intranet.json", {})
    host_keys = _read_json(config_root / "imp-host-keys.json", {})

    threat_log_path = log_root / "imp-threat-log.json"
    threat_log = _read_json(threat_log_path, []) if threat_log_path.exists() else []

    return {
        "processing_security": processing_security,
        "session_security": session_security,
        "intranet": intranet,
        "host_keys": host_keys,
        "threat_log_path": threat_log_path,
        "threat_log_entries": threat_log,
    }


def assess(posture: Dict[str, object]) -> Assessment:
    """Return an assessment capturing issues and advisories."""

    assessment = Assessment()

    processing = posture.get("processing_security", {}) or {}
    session = posture.get("session_security", {}) or {}
    intranet_nodes = (posture.get("intranet", {}) or {}).get("nodes", [])
    host_keys = posture.get("host_keys", {}) or {}
    threat_entries = posture.get("threat_log_entries", []) or []

    # Critical processing controls.
    if not processing.get("require_allowlist", False):
        assessment.issues.append(
            "Processing node allowlist enforcement is disabled; enable "
            "require_allowlist to prevent rogue hosts."
        )
    if processing.get("block_active_threats") is False:
        assessment.issues.append(
            "Processing security is not blocking active threats recorded in "
            "imp-threat-log.json."
        )
    if processing.get("require_host_keys", False) and not host_keys:
        assessment.issues.append(
            "Host key verification is required but imp-host-keys.json does not "
            "list any trusted fingerprints."
        )
    if processing.get("require_intranet_membership", False) and not intranet_nodes:
        assessment.issues.append(
            "Intranet membership is required but no intranet nodes are defined."
        )

    # Session guard expectations.
    if not session.get("require_mfa", False):
        assessment.issues.append("Session guard is not enforcing MFA for operators.")
    idle_minutes = session.get("max_idle_minutes")
    if isinstance(idle_minutes, (int, float)) and idle_minutes > 60:
        assessment.advisories.append(
            "Idle timeout exceeds 60 minutes; consider tightening the value to "
            "reduce session hijack risk."
        )

    # Additional recommendations based on current telemetry.
    if not processing.get("allowed_networks"):
        assessment.advisories.append(
            "Processing security allowed_networks is empty; define trusted "
            "CIDR ranges to minimise lateral movement."
        )
    if not processing.get("allowed_ports"):
        assessment.advisories.append(
            "No allowed_ports specified for processing nodes; explicitly listing "
            "approved service ports hardens ingress policies."
        )
    if threat_entries:
        assessment.advisories.append(
            "Threat log contains %d entrie(s); ensure remediation tasks are "
            "tracked." % len(threat_entries)
        )

    return assessment


def generate_report(posture: Optional[Dict[str, object]] = None) -> str:
    posture = posture if posture is not None else collect_posture()
    assessment = assess(posture)

    lines = ["IMP Zero-Trust Assessment"]
    lines.append("Status: %s" % assessment.status())
    if assessment.issues:
        lines.append("\nIssues:")
        for item in assessment.issues:
            lines.append(f"- {item}")
    if assessment.advisories:
        lines.append("\nAdvisories:")
        for item in assessment.advisories:
            lines.append(f"- {item}")
    if not assessment.issues and not assessment.advisories:
        lines.append("All monitored controls are currently passing.")
    return "\n".join(lines)


def main() -> None:
    print(generate_report())


if __name__ == "__main__":
    main()
