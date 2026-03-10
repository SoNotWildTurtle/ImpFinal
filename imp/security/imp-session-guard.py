"""Session guard for enforcing advanced access hygiene."""

from __future__ import annotations

import argparse
import importlib.util
import ipaddress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "core"
CONFIG_DIR = ROOT / "config"
LOG_DIR = ROOT / "logs"

CONFIG_FILE = CONFIG_DIR / "imp-session-security.json"
AUTH_LOG = LOG_DIR / "imp-auth-log.json"
SESSION_LOG = LOG_DIR / "imp-session-guard.json"
THREAT_LOG = LOG_DIR / "imp-threat-log.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json

DEFAULT_CONFIG: Dict[str, Any] = {
    "max_session_minutes": 240,
    "max_idle_minutes": 20,
    "idle_lock_minutes": 5,
    "require_mfa": True,
    "allowed_origins": ["local", "vpn"],
    "allowed_networks": ["127.0.0.1/32", "10.0.0.0/24"],
    "flagged_roles": ["guest", "external"],
    "record_history": 50,
    "risk_thresholds": {"high": 70, "medium": 40},
    "enable_origin_checks": True,
    "enable_idle_lock": True,
    "block_on_threat": True,
}


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_networks(entries: Iterable[str]) -> List[ipaddress._BaseNetwork]:  # type: ignore[attr-defined]
    networks: List[ipaddress._BaseNetwork] = []  # type: ignore[attr-defined]
    for raw in entries:
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            continue
    return networks


def _match_network(addr: str | None, networks: List[ipaddress._BaseNetwork]) -> bool:  # type: ignore[attr-defined]
    if not addr:
        return False
    try:
        ip_obj = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return any(ip_obj in network for network in networks)


def _score_session(entry: Dict[str, Any], config: Dict[str, Any], now: datetime, networks: List[ipaddress._BaseNetwork]) -> Tuple[int, List[str]]:  # type: ignore[attr-defined]
    score = 0
    reasons: List[str] = []

    if config.get("require_mfa", True) and not entry.get("mfa"):
        score += 35
        reasons.append("MFA not satisfied")

    started = _parse_ts(entry.get("started_at"))
    if started is not None:
        duration = (now - started).total_seconds() / 60
        if duration > config.get("max_session_minutes", 240):
            score += 20
            reasons.append(f"Session duration {duration:.0f}m exceeds limit")
    else:
        reasons.append("Missing start timestamp")
        score += 10

    last_seen = _parse_ts(entry.get("last_seen"))
    if last_seen is not None:
        idle_minutes = (now - last_seen).total_seconds() / 60
        if idle_minutes > config.get("max_idle_minutes", 20):
            score += 20
            reasons.append(f"Idle for {idle_minutes:.0f}m")
        elif config.get("enable_idle_lock", True) and idle_minutes > config.get("idle_lock_minutes", 5):
            reasons.append(f"Idle lock threshold exceeded ({idle_minutes:.0f}m)")
    else:
        score += 5
        reasons.append("Missing last_seen timestamp")

    origin = entry.get("origin")
    if config.get("enable_origin_checks", True) and origin:
        allowed_origins = {item.lower() for item in config.get("allowed_origins", [])}
        if allowed_origins and origin.lower() not in allowed_origins:
            score += 15
            reasons.append(f"Origin {origin} not allowed")

    origin_ip = entry.get("origin_ip")
    if networks and not _match_network(origin_ip, networks):
        score += 15
        reasons.append(f"IP {origin_ip} outside trusted ranges")

    if entry.get("role") in set(config.get("flagged_roles", [])):
        score += 15
        reasons.append(f"Role {entry['role']} under review")

    anomalies = entry.get("anomalies") or []
    for note in anomalies:
        score += 10
        reasons.append(f"Anomaly: {note}")

    if entry.get("geo_anomaly"):
        score += 15
        reasons.append("Geolocation anomaly detected")

    return score, reasons


def _classify(score: int, thresholds: Dict[str, int]) -> str:
    high = thresholds.get("high", 70)
    medium = thresholds.get("medium", 40)
    if score >= high:
        return "high"
    if score >= medium:
        return "medium"
    return "low"


def _read_threat_hosts(path: Path) -> List[str]:
    data = read_json(path, [])
    hosts: List[str] = []
    for item in data:
        host = item.get("host") or item.get("node")
        if host:
            hosts.append(str(host))
    return hosts


def evaluate_sessions(
    config_path: Path = CONFIG_FILE,
    auth_log_path: Path = AUTH_LOG,
    session_log_path: Path = SESSION_LOG,
    threat_log_path: Path = THREAT_LOG,
) -> Dict[str, Any]:
    config = read_json(config_path, DEFAULT_CONFIG)
    thresholds = config.get("risk_thresholds", DEFAULT_CONFIG["risk_thresholds"])  # type: ignore[index]
    networks = _load_networks(config.get("allowed_networks", []))
    sessions: List[Dict[str, Any]] = read_json(auth_log_path, [])
    now = _now()

    flagged: List[Dict[str, Any]] = []
    totals = {"high": 0, "medium": 0, "low": 0}

    for entry in sessions:
        score, reasons = _score_session(entry, config, now, networks)
        level = _classify(score, thresholds)
        totals[level] += 1
        if level != "low":
            flagged.append(
                {
                    "session_id": entry.get("session_id"),
                    "user": entry.get("user"),
                    "role": entry.get("role"),
                    "origin": entry.get("origin"),
                    "origin_ip": entry.get("origin_ip"),
                    "score": score,
                    "level": level,
                    "reasons": reasons,
                }
            )

    recommendations: List[str] = []
    if totals["high"]:
        recommendations.append("Force re-authentication for high-risk sessions and validate MFA tokens.")
    if totals["medium"]:
        recommendations.append("Review medium-risk sessions for policy drift and confirm network location.")
    if not recommendations:
        recommendations.append("No elevated risk detected. Maintain monitoring cadence.")

    threat_hosts = []
    if config.get("block_on_threat", True):
        threat_hosts = _read_threat_hosts(threat_log_path)
        if threat_hosts:
            recommendations.append("Active threat indicators present; restrict processing node hand-offs.")

    summary = {
        "generated_at": now.isoformat(),
        "totals": totals,
        "flagged": flagged,
        "recommendations": recommendations,
        "threat_hosts": threat_hosts,
    }

    history = read_json(session_log_path, [])
    history.append(summary)
    max_records = config.get("record_history", DEFAULT_CONFIG["record_history"])  # type: ignore[index]
    if isinstance(history, list) and len(history) > max_records:
        history = history[-max_records:]
    write_json(session_log_path, history)

    return summary


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate IMP session security state")
    parser.add_argument("--config", type=Path, default=CONFIG_FILE)
    parser.add_argument("--auth-log", dest="auth_log", type=Path, default=AUTH_LOG)
    parser.add_argument("--session-log", dest="session_log", type=Path, default=SESSION_LOG)
    parser.add_argument("--threat-log", dest="threat_log", type=Path, default=THREAT_LOG)
    args = parser.parse_args(argv)

    summary = evaluate_sessions(args.config, args.auth_log, args.session_log, args.threat_log)
    print("Session security summary:")
    print(f"  Generated: {summary['generated_at']}")
    print(f"  Totals: {summary['totals']}")
    if summary["flagged"]:
        print("  Flagged sessions:")
        for item in summary["flagged"]:
            reasons = "; ".join(item["reasons"])
            print(f"    - {item['user']} ({item['session_id']}): score={item['score']} reasons={reasons}")
    else:
        print("  No elevated risk sessions detected.")
    if summary["threat_hosts"]:
        print(f"  Threat hosts: {summary['threat_hosts']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
