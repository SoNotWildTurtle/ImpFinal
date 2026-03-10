"""Security helpers for assessing processing nodes before remote execution."""

from __future__ import annotations

import importlib.util
import ipaddress
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "core"
CONFIG_DIR = ROOT / "config"
LOG_DIR = ROOT / "logs"

CONFIG_FILE = CONFIG_DIR / "imp-processing-security.json"
CLUSTER_NODES_FILE = CONFIG_DIR / "imp-cluster-nodes.json"
INTRANET_CONFIG = CONFIG_DIR / "imp-intranet.json"
HOST_KEYS_FILE = CONFIG_DIR / "imp-host-keys.json"
AUDIT_LOG = LOG_DIR / "imp-network-audit.json"
DIFF_LOG = LOG_DIR / "imp-network-diff.json"
DISCOVERY_LOG = LOG_DIR / "imp-network-discovery.json"
NODE_HEALTH_LOG = LOG_DIR / "imp-node-health.json"
SECURITY_LOG = LOG_DIR / "imp-processing-security.json"
PROCESS_AUDIT_LOG = LOG_DIR / "imp-process-audit.json"
THREAT_LOG = LOG_DIR / "imp-threat-log.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _default_config() -> Dict[str, Any]:
    return {
        "require_allowlist": True,
        "block_unreachable": True,
        "flag_new_or_unknown_hosts": True,
        "alert_on_audit_matches": True,
        "block_slow_hosts": True,
        "block_flapping_hosts": True,
        "block_recent_port_changes": True,
        "block_recent_recovery": False,
        "respect_orchestrator_risk": True,
        "max_latency_ms": None,
        "block_latency_warnings": True,
        "max_latency_warning_streak": None,
        "block_unhealthy_state": True,
        "max_consecutive_failures": None,
        "require_host_keys": False,
        "block_host_key_mismatch": True,
        "host_keys_file": None,
        "require_discovery_data": False,
        "block_stale_discovery": False,
        "max_discovery_age_minutes": None,
        "block_process_audit_matches": False,
        "block_active_threats": True,
        "block_unmatched_threats": False,
        "threat_log_file": None,
        "allowed_networks": [],
        "blocked_networks": [],
        "allowed_ports": [],
        "forbidden_ports": [],
        "allowed_hostname_suffixes": [],
        "require_intranet_membership": False,
        "max_log_entries": 200,
    }


def load_config() -> Dict[str, Any]:
    """Load processing security configuration with defaults."""

    data = read_json(CONFIG_FILE, _default_config())
    if not isinstance(data, dict):
        return _default_config()
    merged = _default_config()
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged


def _allowed_nodes() -> set[str]:
    raw = read_json(CLUSTER_NODES_FILE, [])
    if isinstance(raw, list):
        return {str(item) for item in raw}
    return set()


def _load_audit_ips() -> set[str]:
    entries = read_json(AUDIT_LOG, [])
    suspicious: set[str] = set()
    if isinstance(entries, list):
        for entry in entries:
            remote = None
            if isinstance(entry, dict):
                remote = entry.get("remote")
            if isinstance(remote, str) and remote:
                ip = remote.split(":", 1)[0]
                if ip:
                    suspicious.add(ip)
    return suspicious


def _load_flagged_hosts() -> tuple[set[str], Dict[str, List[str]]]:
    """Return identifiers flagged by network discovery or monitoring."""

    history = read_json(DIFF_LOG, [])
    hosts: set[str] = set()
    reasons: Dict[str, List[str]] = {}

    def add_reason(identifier: str | None, reason: str) -> None:
        if not identifier:
            return
        host = str(identifier)
        hosts.add(host)
        bucket = reasons.setdefault(host, [])
        if reason not in bucket:
            bucket.append(reason)

    if isinstance(history, list) and history:
        last_entry = history[-1]
        if isinstance(last_entry, dict):
            for item in last_entry.get("new_hosts", []) or []:
                if isinstance(item, dict):
                    add_reason(item.get("ip") or item.get("host"), "new_host")
                else:
                    add_reason(item, "new_host")
            for item in last_entry.get("new_ips", []) or []:
                add_reason(item, "new_ip")
            for item in last_entry.get("slow_hosts", []) or []:
                if isinstance(item, dict):
                    add_reason(item.get("ip") or item.get("host"), "slow_host")
            for item in last_entry.get("flapping_hosts", []) or []:
                if isinstance(item, dict):
                    add_reason(item.get("ip") or item.get("host"), "flapping_host")
            for item in last_entry.get("recovered_hosts", []) or []:
                if isinstance(item, dict):
                    add_reason(item.get("ip") or item.get("host"), "recent_recovery")
            for item in last_entry.get("port_changes", []) or []:
                if isinstance(item, dict):
                    add_reason(item.get("ip") or item.get("host"), "port_change")
            summary = last_entry.get("summary")
            if isinstance(summary, dict):
                for item in summary.get("slow_hosts", []) or []:
                    if isinstance(item, dict):
                        add_reason(item.get("ip") or item.get("host"), "slow_host")
                for item in summary.get("flapping_hosts", []) or []:
                    if isinstance(item, dict):
                        add_reason(item.get("ip") or item.get("host"), "flapping_host")
                for item in summary.get("recovered_hosts", []) or []:
                    if isinstance(item, dict):
                        add_reason(item.get("ip") or item.get("host"), "recent_recovery")
                for item in summary.get("port_changes", []) or []:
                    if isinstance(item, dict):
                        add_reason(item.get("ip") or item.get("host"), "port_change")

    return hosts, reasons


def _load_node_health() -> Dict[str, Dict[str, Any]]:
    data = read_json(NODE_HEALTH_LOG, {})
    if isinstance(data, dict):
        return {str(key): value for key, value in data.items() if isinstance(value, dict)}
    return {}


def _resolve_host_keys_file(config_path: Any) -> Path:
    if isinstance(config_path, str) and config_path.strip():
        candidate = Path(config_path).expanduser()
        if not candidate.is_absolute():
            candidate = (CONFIG_DIR / candidate).resolve()
        return candidate
    return HOST_KEYS_FILE


def _resolve_log_override(default: Path, override: Any) -> Path:
    if isinstance(override, str) and override.strip():
        candidate = Path(override).expanduser()
        if not candidate.is_absolute():
            candidate = (default.parent / candidate).resolve()
        return candidate
    return default


def _normalise_fingerprint(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text.lower()


def _load_host_key_policy(config: Dict[str, Any]) -> Dict[str, str]:
    policy: Dict[str, str] = {}

    inline = config.get("allowed_host_keys")
    if isinstance(inline, dict):
        for key, value in inline.items():
            fingerprint = None
            if isinstance(value, dict):
                fingerprint = (
                    value.get("fingerprint")
                    or value.get("ssh")
                    or value.get("ssh_fingerprint")
                )
            else:
                fingerprint = value
            normalised = _normalise_fingerprint(fingerprint)
            if normalised:
                policy[str(key).lower()] = normalised

    host_key_path = _resolve_host_keys_file(config.get("host_keys_file"))
    data = read_json(host_key_path, {})
    if isinstance(data, dict):
        for key, value in data.items():
            fingerprint = None
            if isinstance(value, dict):
                fingerprint = (
                    value.get("fingerprint")
                    or value.get("ssh")
                    or value.get("ssh_fingerprint")
                )
            else:
                fingerprint = value
            normalised = _normalise_fingerprint(fingerprint)
            if normalised:
                policy.setdefault(str(key).lower(), normalised)

    return policy


def _load_process_audit_flags() -> set[str]:
    entries = read_json(PROCESS_AUDIT_LOG, [])
    flagged: set[str] = set()
    if not isinstance(entries, list):
        return flagged
    for entry in entries[::-1]:
        if not isinstance(entry, dict):
            continue
        findings = entry.get("findings")
        if not isinstance(findings, list):
            continue
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            host = finding.get("host") or finding.get("node")
            if isinstance(host, str) and host:
                flagged.add(host.lower())
    return flagged


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value)
    except Exception:  # pragma: no cover - defensive
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _load_discovery_profiles() -> tuple[Dict[str, Dict[str, Any]], str | None]:
    """Return recent network discovery flags keyed by IP or host."""

    entries = read_json(DISCOVERY_LOG, [])
    if not isinstance(entries, list) or not entries:
        return {}, None

    latest = entries[-1]
    if not isinstance(latest, dict):
        return {}, None

    summary = latest.get("summary")
    results = latest.get("results")
    profiles: Dict[str, Dict[str, Any]] = {}

    def profile_for(identifier: str) -> Dict[str, Any]:
        profile = profiles.setdefault(
            identifier,
            {
                "flags": [],
                "latency_ms": None,
                "ports": [],
                "port_changes": [],
                "last_seen": latest.get("timestamp"),
            },
        )
        return profile

    def add_flag(identifier: str, flag: str) -> None:
        if not identifier:
            return
        profile = profile_for(identifier)
        flags = profile.setdefault("flags", [])
        if flag not in flags:
            flags.append(flag)

    if isinstance(summary, dict):
        for item in summary.get("slow_hosts", []) or []:
            if isinstance(item, dict):
                ip = item.get("ip")
                if isinstance(ip, str):
                    profile = profile_for(ip)
                    add_flag(ip, "slow")
                    latency = item.get("latency_ms")
                    if isinstance(latency, (int, float)):
                        profile["latency_ms"] = float(latency)
                    port = item.get("port")
                    if port and port not in profile["ports"]:
                        profile["ports"].append(port)

        for item in summary.get("flapping_hosts", []) or []:
            if isinstance(item, dict):
                ip = item.get("ip")
                if isinstance(ip, str):
                    add_flag(ip, "flapping")

        for item in summary.get("recovered_hosts", []) or []:
            if isinstance(item, dict):
                ip = item.get("ip")
                if isinstance(ip, str):
                    add_flag(ip, "recovered")

        for item in summary.get("port_changes", []) or []:
            if isinstance(item, dict):
                ip = item.get("ip")
                if isinstance(ip, str):
                    profile = profile_for(ip)
                    add_flag(ip, "port_change")
                    changes = profile.setdefault("port_changes", [])
                    if item not in changes:
                        changes.append(item)

    if isinstance(results, list):
        for result in results:
            if not isinstance(result, dict):
                continue
            identifier = result.get("ip") or result.get("host")
            if not isinstance(identifier, str):
                continue
            profile = profile_for(identifier)
            latency = result.get("latency_ms")
            if isinstance(latency, (int, float)):
                profile["latency_ms"] = float(latency)
            port = result.get("port")
            if port and port not in profile["ports"]:
                profile["ports"].append(port)
            hostname = result.get("hostname")
            if isinstance(hostname, str):
                profile["hostname"] = hostname
            if result.get("reachable") is False:
                add_flag(identifier, "unreachable")

    return profiles, latest.get("timestamp")


def _load_threat_entries(config: Dict[str, Any]) -> List[Dict[str, str]]:
    path = _resolve_log_override(THREAT_LOG, config.get("threat_log_file"))
    data = read_json(path, {})
    entries: List[Dict[str, str]] = []

    if isinstance(data, dict):
        for key, value in data.items():
            if not key and not value:
                continue
            entry: Dict[str, str] = {}
            if key:
                entry["type"] = str(key)
            if value not in (None, ""):
                entry["detail"] = str(value)
            if entry:
                entries.append(entry)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                entry: Dict[str, str] = {}
                name = item.get("type") or item.get("name") or item.get("threat")
                if name:
                    entry["type"] = str(name)
                detail = item.get("detail") or item.get("message") or item.get("info")
                if detail:
                    entry["detail"] = str(detail)
                if entry:
                    entries.append(entry)
            elif item:
                entries.append({"type": str(item)})

    return entries


_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HOST_PATTERN = re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b")


def _extract_identifiers_from_text(text: str) -> List[str]:
    """Parse IP or hostname references from free-form text."""

    if not text:
        return []

    matches: List[str] = []
    matches.extend(_IP_PATTERN.findall(text))
    for host in _HOST_PATTERN.findall(text):
        if host not in matches:
            matches.append(host)
    return matches


def _map_threat_hosts(entries: Sequence[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Return mapping of identifiers mentioned in threat entries."""

    mapping: Dict[str, List[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        reasons: List[str] = []
        threat_type = entry.get("type") or entry.get("name") or entry.get("threat")
        detail = entry.get("detail") or entry.get("message")
        if isinstance(threat_type, str) and threat_type.strip():
            reasons.append(threat_type.strip())
        identifiers: List[str] = []
        for key in ("host", "hosts", "ip", "ips", "address", "addresses", "target", "node"):
            value = entry.get(key)
            if isinstance(value, str):
                identifiers.append(value)
            elif isinstance(value, (list, tuple, set)):
                identifiers.extend(str(item) for item in value if item)
        if isinstance(detail, str):
            identifiers.extend(_extract_identifiers_from_text(detail))
        if not identifiers:
            continue
        reason_bucket = reasons or ([detail.strip()] if isinstance(detail, str) and detail.strip() else ["active_threat"])
        for identifier in identifiers:
            ident = str(identifier).strip()
            if not ident:
                continue
            lower = ident.lower()
            bucket = mapping.setdefault(lower, [])
            for reason in reason_bucket:
                if reason and reason not in bucket:
                    bucket.append(reason)
    return mapping


def _parse_networks(values: Sequence[Any] | None) -> List[ipaddress._BaseNetwork]:
    networks: List[ipaddress._BaseNetwork] = []
    if not values:
        return networks
    for item in values:
        if not item:
            continue
        try:
            network = ipaddress.ip_network(str(item), strict=False)
        except ValueError:
            continue
        networks.append(network)
    return networks


def _normalise_port_set(values: Sequence[Any] | None) -> set[int]:
    ports: set[int] = set()
    if not values:
        return ports
    for value in values:
        try:
            port = int(value)
        except (TypeError, ValueError):
            continue
        if 0 < port < 65536:
            ports.add(port)
    return ports


def _identifier_in_network(identifier: str, networks: Sequence[ipaddress._BaseNetwork]) -> bool:
    if not networks or not identifier:
        return False
    try:
        ip_value = ipaddress.ip_address(identifier)
    except ValueError:
        return False
    return any(ip_value in network for network in networks)


def _load_intranet_policy() -> tuple[set[str], List[ipaddress._BaseNetwork]]:
    data = read_json(INTRANET_CONFIG, {})
    entries: Iterable[Any]
    if isinstance(data, dict):
        entries = data.get("nodes", []) or []
    elif isinstance(data, list):
        entries = data
    else:
        entries = []

    identifiers: set[str] = set()
    networks: List[ipaddress._BaseNetwork] = []
    for item in entries:
        if not item:
            continue
        item_str = str(item).strip()
        if not item_str:
            continue
        try:
            networks.append(ipaddress.ip_network(item_str, strict=False))
            continue
        except ValueError:
            identifiers.add(item_str.lower())
    return identifiers, networks


def _matches_suffix(host: str, suffixes: Sequence[str]) -> bool:
    if not host or not suffixes:
        return False
    lowered = host.lower()
    return any(lowered.endswith(suffix.lower()) for suffix in suffixes if suffix)


def _max_latency(config: Dict[str, Any]) -> float | None:
    raw_value = config.get("max_latency_ms")
    if raw_value in (None, "", False):
        return None
    try:
        latency = float(raw_value)
    except (TypeError, ValueError):
        return None
    return latency if latency > 0 else None


def _match_addresses(target: str, addresses: Iterable[str]) -> bool:
    if not target:
        return False
    try:
        target_ip = ipaddress.ip_address(target)
    except ValueError:
        target_ip = None
    lowered_target = target.lower()
    for address in addresses:
        if not isinstance(address, str):
            continue
        if address.lower() == lowered_target:
            return True
        if target_ip is not None:
            try:
                if ipaddress.ip_address(address) == target_ip:
                    return True
            except ValueError:
                continue
    return False


def assess_processing_nodes(
    nodes: Sequence[str],
    *,
    statuses: Sequence[Dict[str, Any]] | None = None,
    meta: Dict[str, Any] | None = None,
    orchestrator_plan: Dict[str, Any] | None = None,
    backlog: int | None = None,
) -> Dict[str, Any]:
    """Return security assessment for requested processing nodes."""

    config = load_config()
    allowlist = _allowed_nodes()
    suspicious_ips = _load_audit_ips() if config.get("alert_on_audit_matches", True) else set()
    flagged_hosts: set[str]
    flagged_reasons: Dict[str, List[str]]
    if config.get("flag_new_or_unknown_hosts", True):
        flagged_hosts, flagged_reasons = _load_flagged_hosts()
    else:
        flagged_hosts, flagged_reasons = set(), {}
    discovery_profiles, discovery_timestamp = _load_discovery_profiles()
    max_latency = _max_latency(config)
    allowed_networks = _parse_networks(config.get("allowed_networks"))
    blocked_networks = _parse_networks(config.get("blocked_networks"))
    allowed_ports = _normalise_port_set(config.get("allowed_ports"))
    forbidden_ports = _normalise_port_set(config.get("forbidden_ports"))
    hostname_suffixes = [str(item).lower() for item in config.get("allowed_hostname_suffixes", []) or [] if item]
    require_intranet = bool(config.get("require_intranet_membership"))
    if require_intranet:
        intranet_identifiers, intranet_networks = _load_intranet_policy()
    else:
        intranet_identifiers, intranet_networks = set(), []
    host_key_policy = _load_host_key_policy(config)
    require_host_keys = bool(config.get("require_host_keys"))
    block_host_key_mismatch = bool(config.get("block_host_key_mismatch", True))
    process_audit_flags = (
        _load_process_audit_flags() if config.get("block_process_audit_matches") else set()
    )
    threat_entries = _load_threat_entries(config)
    threat_hosts = _map_threat_hosts(threat_entries)
    block_active_threats = bool(config.get("block_active_threats", True)) and bool(threat_entries)
    block_unmatched_threats = bool(config.get("block_unmatched_threats", False))

    discovery_age_minutes = None
    discovery_missing = discovery_timestamp is None
    stale_discovery = False
    if discovery_timestamp:
        parsed = _parse_timestamp(discovery_timestamp)
        if parsed:
            delta = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
            discovery_age_minutes = max(0.0, delta.total_seconds() / 60.0)
            threshold = config.get("max_discovery_age_minutes")
            if isinstance(threshold, (int, float)) and threshold >= 0:
                if discovery_age_minutes > float(threshold):
                    stale_discovery = True
        else:
            discovery_missing = True
    elif config.get("require_discovery_data"):
        discovery_missing = True

    status_map: Dict[str, Dict[str, Any]] = {}
    if statuses:
        for status in statuses:
            host = status.get("host")
            if isinstance(host, str):
                status_map[host] = status

    allowed_nodes: List[str] = []
    blocked_nodes: List[Dict[str, Any]] = []
    network_matches: List[Dict[str, Any]] = []
    health_indicators = _load_node_health()
    health_matches: List[Dict[str, Any]] = []
    flagged_summary: Dict[str, List[str]] = {}
    threat_host_summary: Dict[str, List[str]] = {}

    risk_nodes: set[str] = set()
    if orchestrator_plan:
        raw_risk = orchestrator_plan.get("risk_nodes")
        if isinstance(raw_risk, dict):
            raw_risk = raw_risk.values()
        if isinstance(raw_risk, (list, tuple, set)):
            risk_nodes = {str(item) for item in raw_risk if item}
        elif isinstance(raw_risk, str):
            risk_nodes = {raw_risk}

    for node in nodes:
        issues: List[str] = []
        node_status = status_map.get(node, {})
        addresses = node_status.get("addresses") or []
        addresses = [str(addr) for addr in addresses if addr]
        identifiers = [node, *addresses]

        if config.get("require_allowlist", True) and allowlist and node not in allowlist:
            issues.append("not_allowlisted")

        if config.get("block_unreachable", True) and node_status:
            if not node_status.get("reachable"):
                issues.append("unreachable")

        if discovery_missing and config.get("require_discovery_data"):
            issues.append("missing_discovery")
        if stale_discovery and config.get("block_stale_discovery"):
            issues.append("stale_discovery")

        # Flag if node or any of its addresses appear in recent network diff output.
        if flagged_hosts:
            matched_reasons: List[str] = []
            identifiers_to_check = [node, *addresses]
            for identifier in identifiers_to_check:
                if not identifier:
                    continue
                direct_reasons = flagged_reasons.get(identifier, [])
                if direct_reasons:
                    matched_reasons.extend(direct_reasons)
                    continue
                for flagged_identifier, reason_list in flagged_reasons.items():
                    if _match_addresses(flagged_identifier, [identifier]):
                        matched_reasons.extend(reason_list)
            if matched_reasons:
                issues.append("network_diff_flag")
                flagged_summary[node] = sorted(set(matched_reasons))

        # Flag nodes that appear in network audit suspicious connections.
        if suspicious_ips:
            if node in suspicious_ips or any(_match_addresses(ip, [node]) or _match_addresses(ip, addresses) for ip in suspicious_ips):
                issues.append("network_audit_flag")

        if process_audit_flags:
            for identifier in identifiers:
                if identifier and identifier.lower() in process_audit_flags:
                    issues.append("process_audit_flag")
                    break

        if hostname_suffixes:
            try:
                ipaddress.ip_address(node)
                hostname_valid = True
            except ValueError:
                hostname_valid = _matches_suffix(node, hostname_suffixes)
            if not hostname_valid:
                issues.append("hostname_policy_violation")

        if allowed_networks and not any(_identifier_in_network(identifier, allowed_networks) for identifier in identifiers):
            issues.append("outside_allowed_networks")

        if blocked_networks and any(_identifier_in_network(identifier, blocked_networks) for identifier in identifiers):
            issues.append("blocked_network")

        if require_intranet:
            intranet_ok = False
            for identifier in identifiers:
                if not identifier:
                    continue
                lowered = identifier.lower()
                if lowered in intranet_identifiers or _identifier_in_network(identifier, intranet_networks):
                    intranet_ok = True
                    break
            if not intranet_ok:
                issues.append("not_intranet_member")

        matched_profiles: List[Dict[str, Any]] = []
        observed_ports: set[int] = set()
        for identifier in [node, *addresses]:
            profile = discovery_profiles.get(identifier)
            if not profile:
                continue
            entry = {"identifier": identifier, **profile}
            matched_profiles.append(entry)
            flags = profile.get("flags", [])
            if config.get("block_slow_hosts", True) and "slow" in flags:
                issues.append("slow_host")
            if config.get("block_flapping_hosts", True) and "flapping" in flags:
                issues.append("flapping_host")
            if config.get("block_recent_port_changes", True) and profile.get("port_changes"):
                issues.append("recent_port_change")
            if config.get("block_recent_recovery", False) and "recovered" in flags:
                issues.append("recent_recovery")
            if max_latency is not None:
                latency = profile.get("latency_ms")
                if isinstance(latency, (int, float)) and latency > max_latency:
                    issues.append("latency_threshold")
            ports = profile.get("ports") or []
            for port in ports:
                try:
                    observed_ports.add(int(port))
                except (TypeError, ValueError):
                    continue

        if matched_profiles:
            network_matches.append({"host": node, "profiles": matched_profiles})

        if observed_ports:
            if allowed_ports and any(port not in allowed_ports for port in observed_ports):
                issues.append("port_not_allowed")
            if forbidden_ports and any(port in forbidden_ports for port in observed_ports):
                issues.append("forbidden_port")

        metadata = node_status.get("metadata") if isinstance(node_status, dict) else {}
        observed_fingerprint = None
        fingerprint_candidates: List[Any] = []
        if isinstance(metadata, dict):
            fingerprint_candidates.extend(
                metadata.get(key) for key in ("ssh_fingerprint", "fingerprint", "host_key", "ssh")
            )
        fingerprint_candidates.extend(
            node_status.get(key) for key in ("ssh_fingerprint", "fingerprint", "host_key") if isinstance(node_status, dict)
        )
        if health_info and isinstance(health_info, dict):
            fingerprint_candidates.extend(
                health_info.get(key) for key in ("ssh_fingerprint", "fingerprint", "host_key")
            )
        for candidate in fingerprint_candidates:
            normalised = _normalise_fingerprint(candidate)
            if normalised:
                observed_fingerprint = normalised
                break

        required_fingerprint = None
        for identifier in identifiers:
            if not identifier:
                continue
            mapped = host_key_policy.get(identifier.lower())
            if mapped:
                required_fingerprint = mapped
                break

        if require_host_keys and not required_fingerprint:
            issues.append("host_key_not_allowlisted")
        if required_fingerprint:
            if observed_fingerprint is None:
                if require_host_keys:
                    issues.append("host_key_missing")
            elif observed_fingerprint != required_fingerprint and block_host_key_mismatch:
                issues.append("host_key_mismatch")

        health_info = None
        candidate_keys = [node, node.lower()]
        candidate_keys.extend(addresses)
        for key in candidate_keys:
            if not key:
                continue
            entry = health_indicators.get(key)
            if entry:
                health_info = entry
                break

        if health_info:
            captured = {
                key: health_info.get(key)
                for key in (
                    "state",
                    "latency_state",
                    "latency_warning_streak",
                    "consecutive_failures",
                    "flapping",
                    "last_seen",
                )
                if key in health_info
            }
            if captured:
                health_matches.append({"host": node, "health": captured})

            if config.get("block_latency_warnings", True):
                if health_info.get("latency_state") == "slow" or int(health_info.get("latency_warning_streak", 0) or 0) > 0:
                    issues.append("latency_warning")

            max_warning_streak = config.get("max_latency_warning_streak")
            if isinstance(max_warning_streak, int) and max_warning_streak >= 0:
                if int(health_info.get("latency_warning_streak", 0) or 0) > max_warning_streak:
                    issues.append("latency_warning_streak")

            if config.get("block_unhealthy_state", True):
                state = health_info.get("state")
                if state and str(state).lower() not in {"online", "healthy"}:
                    issues.append("unhealthy_state")

            max_failures = config.get("max_consecutive_failures")
            if isinstance(max_failures, int) and max_failures >= 0:
                if int(health_info.get("consecutive_failures", 0) or 0) > max_failures:
                    issues.append("consecutive_failures")

        if config.get("respect_orchestrator_risk", True) and node in risk_nodes:
            issues.append("orchestrator_risk")

        threat_matches: List[str] = []
        if block_active_threats and threat_hosts:
            for threat_identifier, reasons in threat_hosts.items():
                if _match_addresses(threat_identifier, identifiers):
                    for reason in reasons:
                        if reason not in threat_matches:
                            threat_matches.append(reason)
        if threat_matches:
            issues.append("active_threat")
            threat_host_summary[node] = sorted(threat_matches)
        elif block_active_threats and block_unmatched_threats:
            issues.append("active_threat")

        if issues:
            blocked_nodes.append({"host": node, "issues": sorted(set(issues))})
        else:
            allowed_nodes.append(node)

    summary = {
        "timestamp": _now(),
        "requested": list(nodes),
        "allowed_nodes": allowed_nodes,
        "blocked_nodes": blocked_nodes,
        "meta": meta or {},
    }
    if orchestrator_plan:
        summary["orchestrator"] = {
            "confidence": orchestrator_plan.get("confidence"),
            "strategy": orchestrator_plan.get("strategy"),
            "risk_nodes": orchestrator_plan.get("risk_nodes"),
        }
    if backlog is not None:
        summary["backlog"] = backlog
    if network_matches:
        summary["network_matches"] = network_matches
    if health_matches:
        summary["health_matches"] = health_matches
    if flagged_summary:
        summary["flagged_host_reasons"] = flagged_summary
    if threat_entries:
        summary["threats"] = threat_entries
        summary["threat_blocking"] = block_active_threats
        if threat_host_summary:
            summary["threat_host_matches"] = threat_host_summary
    if discovery_timestamp or discovery_age_minutes is not None or discovery_missing:
        summary["discovery_metadata"] = {
            "timestamp": discovery_timestamp,
            "age_minutes": discovery_age_minutes,
            "stale": stale_discovery,
            "missing": discovery_missing,
        }
    if host_key_policy:
        summary["host_key_policy"] = {
            "required": require_host_keys,
            "known_hosts": len(host_key_policy),
        }
    if process_audit_flags:
        summary["process_audit_checks"] = len(process_audit_flags)

    log_entries = read_json(SECURITY_LOG, [])
    if not isinstance(log_entries, list):
        log_entries = []
    log_entries.append(summary)
    max_entries = config.get("max_log_entries")
    if isinstance(max_entries, int) and max_entries > 0 and len(log_entries) > max_entries:
        log_entries = log_entries[-max_entries:]
    write_json(SECURITY_LOG, log_entries)

    return summary


__all__ = ["assess_processing_nodes", "load_config"]
