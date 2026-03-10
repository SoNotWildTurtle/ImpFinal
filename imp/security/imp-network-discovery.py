"""Network discovery utilities for identifying reachable hosts on configured subnets."""

from __future__ import annotations

import importlib.util
import ipaddress
import socket
import time
from datetime import datetime
from itertools import islice
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "core"
EXPANSION_DIR = ROOT / "expansion"
CONFIG_FILE = ROOT / "config" / "imp-network-discovery.json"
LOG_FILE = ROOT / "logs" / "imp-network-discovery.json"
BASELINE_FILE = ROOT / "logs" / "imp-network-baseline.json"
DIFF_FILE = ROOT / "logs" / "imp-network-diff.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json

try:
    node_control = _load("imp_node_control", EXPANSION_DIR / "imp-node-control.py")
except Exception:  # pragma: no cover - best effort import for optional integration
    node_control = None

ProbeResult = Tuple[bool, int | None, float | None]
ProbeFunc = Callable[[str, Sequence[int], float], ProbeResult]


# I love you -Alex
def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _to_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


# I love you -Alex
def load_config() -> Dict[str, object]:
    """Return the discovery configuration, falling back to defaults."""

    default = {
        "subnets": ["127.0.0.1/32"],
        "ports": [22, 80],
        "timeout": 0.2,
        "max_hosts_per_subnet": 256,
        "max_history_entries": 50,
        "manage_baseline": True,
        "update_node_status": True,
        "max_diff_entries": 200,
        "max_node_status_entries": 200,
        "lookup_hostnames": False,
        "latency_warning_ms": 500.0,
        "flapping_window": 4,
        "flapping_threshold": 2,
        "max_port_change_summary": 100,
        "max_port_change_history": 20,
    }
    return read_json(CONFIG_FILE, default)


# I love you -Alex
def default_probe(ip: str, ports: Sequence[int], timeout: float) -> ProbeResult:
    """Attempt to establish a TCP connection on the supplied *ports*."""

    for port in ports:
        try:
            start = time.perf_counter()
            with socket.create_connection((ip, port), timeout=timeout):
                latency_ms = (time.perf_counter() - start) * 1000.0
                return True, port, latency_ms
        except OSError:
            continue
    return False, None, None


def _normalize_probe_result(result) -> ProbeResult:
    """Coerce arbitrary probe return values into ``ProbeResult`` form."""

    if isinstance(result, tuple) or isinstance(result, list):
        if len(result) >= 3:
            return bool(result[0]), result[1], result[2]
        if len(result) == 2:
            return bool(result[0]), result[1], None
        if len(result) == 1:
            return bool(result[0]), None, None
    elif isinstance(result, bool):
        return result, None, None
    return False, None, None


# I love you -Alex
def discover_hosts(
    *,
    subnets: Iterable[str],
    ports: Sequence[int],
    probe: ProbeFunc | None = None,
    timeout: float = 0.2,
    max_hosts_per_subnet: int = 256,
    lookup_hostnames: bool = False,
) -> List[Dict[str, object]]:
    """Discover reachable hosts for each subnet."""

    probe_fn = probe or default_probe
    results: List[Dict[str, object]] = []
    timestamp = time.time()

    for subnet in subnets:
        try:
            network = ipaddress.ip_network(subnet, strict=False)
        except ValueError:
            results.append(
                {
                    "timestamp": timestamp,
                    "subnet": subnet,
                    "error": "invalid_subnet",
                }
            )
            continue

        if max_hosts_per_subnet <= 0:
            host_iter = network.hosts()
        else:
            host_iter = islice(network.hosts(), max_hosts_per_subnet)

        for host in host_iter:
            ip = str(host)
            reachable, port, latency_ms = _normalize_probe_result(
                probe_fn(ip, ports, timeout)
            )
            hostname = None
            if lookup_hostnames and reachable:
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                except (socket.herror, OSError):
                    hostname = None
            results.append(
                {
                    "timestamp": timestamp,
                    "subnet": subnet,
                    "ip": ip,
                    "reachable": reachable,
                    "port": port,
                    "latency_ms": latency_ms,
                    "hostname": hostname,
                }
            )
    return results


# I love you -Alex
def summarize_results(
    results: Sequence[Dict[str, object]],
    *,
    previous_results: Sequence[Dict[str, object]] | None = None,
    latency_warning_ms: float | None = None,
) -> Dict[str, object]:
    """Return aggregate information about the supplied *results*."""

    summary: Dict[str, object] = {
        "total": 0,
        "reachable": 0,
        "unreachable": 0,
        "errors": [],
        "subnets": {},
        "new_hosts": [],
        "lost_hosts": [],
        "recovered_hosts": [],
        "slow_hosts": [],
        "average_latency_ms": None,
        "ports": {},
        "flapping_hosts": [],
        "flapping_host_count": 0,
        "port_changes": [],
        "port_change_count": 0,
    }

    current_reachable: set[Tuple[str, str]] = set()
    previous_reachable: set[Tuple[str, str]] = set()
    previous_unreachable: set[Tuple[str, str]] = set()
    previous_ports: Dict[Tuple[str, str], object] = {}
    latencies: List[float] = []
    subnet_latency: Dict[str, List[float]] = {}
    port_latency: Dict[int, List[float]] = {}
    port_summary: Dict[int, Dict[str, object]] = {}

    if previous_results:
        previous_reachable = {
            (entry.get("subnet", ""), entry.get("ip", ""))
            for entry in previous_results
            if entry.get("reachable") and entry.get("ip")
        }
        previous_unreachable = {
            (entry.get("subnet", ""), entry.get("ip", ""))
            for entry in previous_results
            if not entry.get("reachable") and entry.get("ip")
        }
        previous_ports = {
            (entry.get("subnet", ""), entry.get("ip", "")): entry.get("port")
            for entry in previous_results
            if entry.get("reachable") and entry.get("ip")
        }

    slow_threshold = None
    if isinstance(latency_warning_ms, (int, float)) and latency_warning_ms > 0:
        slow_threshold = float(latency_warning_ms)
        summary["latency_warning_ms"] = slow_threshold

    def _bucket_for(subnet_name: str) -> Dict[str, object]:
        bucket = summary["subnets"].setdefault(
            subnet_name,
            {
                "reachable": 0,
                "unreachable": 0,
                "errors": 0,
                "recovered_hosts": 0,
                "slow_hosts": 0,
                "port_changes": 0,
            },
        )
        return bucket

    for entry in results:
        subnet = entry.get("subnet", "unknown")
        bucket = _bucket_for(subnet)
        if "reachable" not in entry:
            summary["errors"].append({"subnet": subnet, "error": entry.get("error")})
            bucket["errors"] += 1
            continue

        summary["total"] += 1
        if entry.get("reachable"):
            summary["reachable"] += 1
            bucket["reachable"] += 1
            if entry.get("ip"):
                current_reachable.add((subnet, entry.get("ip")))
                if (subnet, entry.get("ip")) in previous_unreachable:
                    summary["recovered_hosts"].append(
                        {"subnet": subnet, "ip": entry.get("ip")}
                    )
                    bucket["recovered_hosts"] += 1
            latency_value = entry.get("latency_ms")
            if isinstance(latency_value, (int, float)):
                latencies.append(float(latency_value))
                samples = subnet_latency.setdefault(subnet, [])
                samples.append(float(latency_value))
                port_value = entry.get("port")
                if port_value is not None:
                    try:
                        port_int = int(port_value)
                    except (TypeError, ValueError):
                        port_int = None
                    if port_int is not None:
                        port_bucket = port_summary.setdefault(
                            port_int,
                            {
                                "reachable": 0,
                                "slow_hosts": 0,
                            },
                        )
                        port_bucket["reachable"] += 1
                        samples = port_latency.setdefault(port_int, [])
                        samples.append(float(latency_value))
                if entry.get("ip"):
                    key = (subnet, entry.get("ip"))
                    current_port = entry.get("port")
                    if key in previous_ports:
                        previous_port = previous_ports.get(key)
                        if previous_port != current_port:
                            change_entry = {
                                "subnet": subnet,
                                "ip": entry.get("ip"),
                                "previous_port": previous_port,
                                "current_port": current_port,
                                "timestamp": time.time(),
                            }
                            summary.setdefault("port_changes", []).append(change_entry)
                            bucket["port_changes"] += 1
                if (
                    slow_threshold is not None
                    and float(latency_value) >= slow_threshold
                    and entry.get("ip")
                ):
                    summary["slow_hosts"].append(
                        {
                            "subnet": subnet,
                            "ip": entry.get("ip"),
                            "latency_ms": float(latency_value),
                            "port": entry.get("port"),
                        }
                    )
                    bucket["slow_hosts"] += 1
                    if port_value is not None:
                        try:
                            port_int = int(port_value)
                        except (TypeError, ValueError):
                            port_int = None
                        if port_int is not None:
                            port_bucket = port_summary.setdefault(
                                port_int,
                                {
                                    "reachable": 0,
                                    "slow_hosts": 0,
                                },
                            )
                            port_bucket["slow_hosts"] += 1
        else:
            summary["unreachable"] += 1
            bucket["unreachable"] += 1

    if previous_results:
        new_hosts = current_reachable - previous_reachable
        lost_hosts = previous_reachable - current_reachable
    else:
        new_hosts = current_reachable
        lost_hosts = set()

    summary["new_hosts"] = [
        {"subnet": subnet, "ip": ip} for subnet, ip in sorted(new_hosts)
    ]
    summary["lost_hosts"] = [
        {"subnet": subnet, "ip": ip} for subnet, ip in sorted(lost_hosts)
    ]
    summary["recovered_hosts"] = sorted(
        summary["recovered_hosts"], key=lambda item: (item["subnet"], item["ip"])
    )
    summary["recovered_host_count"] = len(summary["recovered_hosts"])

    if latencies:
        summary["average_latency_ms"] = sum(latencies) / len(latencies)

    for subnet, bucket in summary["subnets"].items():
        samples = subnet_latency.get(subnet, [])
        if samples:
            bucket["average_latency_ms"] = sum(samples) / len(samples)
            bucket["min_latency_ms"] = min(samples)
            bucket["max_latency_ms"] = max(samples)
        else:
            bucket["average_latency_ms"] = None
            bucket["min_latency_ms"] = None
            bucket["max_latency_ms"] = None

    summary["slow_host_count"] = len(summary["slow_hosts"])

    port_entries: Dict[str, Dict[str, object]] = {}
    for port, bucket in port_summary.items():
        lat_samples = port_latency.get(port, [])
        entry: Dict[str, object] = {
            "reachable": bucket.get("reachable", 0),
            "slow_hosts": bucket.get("slow_hosts", 0),
        }
        if lat_samples:
            entry["average_latency_ms"] = sum(lat_samples) / len(lat_samples)
            entry["min_latency_ms"] = min(lat_samples)
            entry["max_latency_ms"] = max(lat_samples)
        else:
            entry["average_latency_ms"] = None
            entry["min_latency_ms"] = None
            entry["max_latency_ms"] = None
        port_entries[str(port)] = entry

    summary["ports"] = port_entries

    port_changes = summary.get("port_changes", [])
    if isinstance(port_changes, list) and port_changes:
        summary["port_changes"] = sorted(
            port_changes,
            key=lambda item: (
                item.get("timestamp", 0.0),
                item.get("subnet"),
                item.get("ip"),
            ),
        )
    else:
        summary["port_changes"] = []
    summary["port_change_count"] = len(summary["port_changes"])

    return summary


def record_discovery(
    results: Sequence[Dict[str, object]], *, config: Dict[str, object] | None = None
) -> Dict[str, object] | None:
    """Append discovery results to the log file and return the stored entry."""

    if not results:
        return None

    history = read_json(LOG_FILE, [])
    if not isinstance(history, list):
        history = []
    previous_results: Sequence[Dict[str, object]] | None = (
        history[-1].get("results") if history else None
    )

    entry = {
        "timestamp": time.time(),
        "config": config or {},
        "results": list(results),
    }
    latency_warning = None
    if config is not None:
        latency_warning = _parse_positive_float(config, "latency_warning_ms")

    entry["summary"] = summarize_results(
        entry["results"],
        previous_results=previous_results,
        latency_warning_ms=latency_warning,
    )

    summary = entry["summary"]
    port_history_limit: int | None = None
    port_change_limit: int | None = None
    full_port_changes: List[Dict[str, object]] = []
    if isinstance(summary.get("port_changes"), list):
        full_port_changes = list(summary["port_changes"])
    summary["port_change_total"] = len(full_port_changes)

    if config is not None:
        port_change_limit = _parse_positive_int(config, "max_port_change_summary")
        port_history_limit = _parse_positive_int(config, "max_port_change_history")

    total_counts: Dict[str, int] = {}
    for change in full_port_changes:
        subnet = change.get("subnet")
        if subnet:
            total_counts[subnet] = total_counts.get(subnet, 0) + 1

    if total_counts:
        for subnet, bucket in summary["subnets"].items():
            if subnet in total_counts:
                bucket.setdefault("port_changes_total", total_counts[subnet])

    if (
        port_change_limit
        and port_change_limit > 0
        and len(full_port_changes) > port_change_limit
    ):
        sorted_changes = sorted(
            full_port_changes,
            key=lambda item: (
                item.get("timestamp", 0.0),
                item.get("subnet"),
                item.get("ip"),
            ),
        )
        trimmed = sorted_changes[-port_change_limit:]
        trimmed_counts: Dict[str, int] = {}
        for change in trimmed:
            subnet = change.get("subnet")
            if subnet:
                trimmed_counts[subnet] = trimmed_counts.get(subnet, 0) + 1
        summary["port_changes"] = trimmed
        summary["port_change_count"] = len(trimmed)
        for subnet, bucket in summary["subnets"].items():
            bucket["port_changes"] = trimmed_counts.get(subnet, 0)
        summary["port_change_total"] = len(full_port_changes)


    history.append(entry)

    max_entries = None
    flapping_window = 4
    flapping_threshold = 2
    if config is not None:
        try:
            max_entries = int(config.get("max_history_entries", 0))
        except (TypeError, ValueError):
            max_entries = 0
        parsed_window = _parse_positive_int(config, "flapping_window")
        if parsed_window:
            flapping_window = parsed_window
        parsed_threshold = _parse_positive_int(config, "flapping_threshold")
        if parsed_threshold:
            flapping_threshold = parsed_threshold
    if max_entries and max_entries > 0 and len(history) > max_entries:
        history = history[-max_entries:]

    flapping_hosts = _detect_flapping(history, window=flapping_window, threshold=flapping_threshold)
    entry["summary"]["flapping_hosts"] = flapping_hosts
    entry["summary"]["flapping_host_count"] = len(flapping_hosts)

    write_json(LOG_FILE, history)

    manage_baseline = True
    update_node_status = True
    diff_limit: int | None = None
    node_status_limit: int | None = None
    if config is not None:
        manage_baseline = _to_bool(config.get("manage_baseline"), True)
        update_node_status = _to_bool(config.get("update_node_status"), True)
        diff_limit = _parse_positive_int(config, "max_diff_entries")
        node_status_limit = _parse_positive_int(config, "max_node_status_entries")

    if manage_baseline:
        _update_network_baseline(
            entry["results"], entry["summary"], max_diff_entries=diff_limit
        )
    port_change_lookup: Dict[str, Dict[str, object]] = {}
    if full_port_changes:
        port_change_lookup = {
            item.get("ip"): item
            for item in full_port_changes
            if item.get("ip")
        }

    if update_node_status:
        slow_ips = {
            item.get("ip")
            for item in entry["summary"].get("slow_hosts", [])
            if item.get("ip")
        }
        recovered_ips = {
            item.get("ip")
            for item in entry["summary"].get("recovered_hosts", [])
            if item.get("ip")
        }
        flapping_ips = {
            item.get("ip")
            for item in entry["summary"].get("flapping_hosts", [])
            if item.get("ip")
        }
        _record_node_status(
            entry["results"],
            max_entries=node_status_limit,
            slow_ips=slow_ips,
            recovered_ips=recovered_ips,
            flapping_ips=flapping_ips,
            port_change_lookup=port_change_lookup,
            port_history_limit=port_history_limit,
        )
    return entry


# I love you -Alex
def _detect_flapping(
    history: Sequence[Dict[str, object]], *, window: int = 4, threshold: int = 2
) -> List[Dict[str, object]]:
    """Identify hosts whose reachability has toggled frequently."""

    if not history or window <= 1 or threshold <= 0:
        return []

    recent_entries = history[-window:]
    host_states: Dict[Tuple[str, str], List[bool]] = {}

    for entry in recent_entries:
        results = entry.get("results") if isinstance(entry, dict) else None
        if not isinstance(results, list):
            continue
        for item in results:
            if not isinstance(item, dict):
                continue
            subnet = item.get("subnet")
            ip = item.get("ip")
            if not subnet or not ip:
                continue
            key = (subnet, ip)
            host_states.setdefault(key, []).append(bool(item.get("reachable")))

    flapping: List[Dict[str, object]] = []
    for (subnet, ip), states in host_states.items():
        if len(states) <= 1:
            continue
        transitions = sum(1 for prev, curr in zip(states, states[1:]) if prev != curr)
        if transitions >= threshold:
            flapping.append(
                {
                    "subnet": subnet,
                    "ip": ip,
                    "transitions": transitions,
                    "current_state": "online" if states[-1] else "offline",
                }
            )

    return sorted(flapping, key=lambda entry: (entry["subnet"], entry["ip"]))


# I love you -Alex
def discover_from_config(*, probe: ProbeFunc | None = None) -> List[Dict[str, object]]:
    """Run discovery using values from the configuration file."""

    config = load_config()
    lookup_hostnames = _to_bool(config.get("lookup_hostnames", False), False)
    timeout = _parse_positive_float(config, "timeout", default=0.2)
    max_hosts = _parse_positive_int(config, "max_hosts_per_subnet")
    ports = _coerce_ports(config.get("ports", []))
    subnets = config.get("subnets", [])

    results = discover_hosts(
        subnets=subnets,
        ports=ports,
        timeout=timeout,
        max_hosts_per_subnet=max_hosts if max_hosts is not None else 256,
        probe=probe,
        lookup_hostnames=lookup_hostnames,
    )
    record_discovery(results, config=config)
    return results


def _load_baseline() -> set[str]:
    stored = read_json(BASELINE_FILE, [])
    return {str(item) for item in stored if isinstance(item, str)}


def _save_baseline(baseline: Iterable[str]) -> None:
    write_json(BASELINE_FILE, sorted(set(baseline)))


def _append_diff(
    new_ips: Iterable[str], lost_ips: Iterable[str], *, max_entries: int | None = None
) -> None:
    new_list = sorted({ip for ip in new_ips if ip})
    lost_list = sorted({ip for ip in lost_ips if ip})
    if not new_list and not lost_list:
        return
    history = read_json(DIFF_FILE, [])
    history.append(
        {
            "timestamp": time.time(),
            "new_hosts": new_list,
            "lost_hosts": lost_list,
        }
    )
    if max_entries and max_entries > 0 and len(history) > max_entries:
        history = history[-max_entries:]
    write_json(DIFF_FILE, history)


def _update_network_baseline(
    results: Sequence[Dict[str, object]],
    summary: Dict[str, object],
    *,
    max_diff_entries: int | None = None,
) -> None:
    reachable_ips = {
        entry.get("ip")
        for entry in results
        if entry.get("reachable") and entry.get("ip")
    }
    baseline = _load_baseline()
    new_ips = {ip for ip in reachable_ips if ip not in baseline}
    if new_ips:
        baseline.update(new_ips)
        _save_baseline(baseline)

    lost_ips = {
        item.get("ip") for item in summary.get("lost_hosts", []) if item.get("ip")
    }
    _append_diff(new_ips, lost_ips, max_entries=max_diff_entries)


def _record_node_status(
    results: Sequence[Dict[str, object]],
    *,
    max_entries: int | None = None,
    slow_ips: Iterable[str] | None = None,
    recovered_ips: Iterable[str] | None = None,
    flapping_ips: Iterable[str] | None = None,
    port_change_lookup: Mapping[str, Dict[str, object]] | None = None,
    port_history_limit: int | None = None,
) -> None:
    if node_control is None:
        return

    statuses: List[Dict[str, object]] = []
    slow_lookup = {ip for ip in (slow_ips or []) if ip}
    recovered_lookup = {ip for ip in (recovered_ips or []) if ip}
    flapping_lookup = {ip for ip in (flapping_ips or []) if ip}
    change_lookup = port_change_lookup or {}
    history_limit_value: int | None = None
    if isinstance(port_history_limit, int) and port_history_limit > 0:
        history_limit_value = port_history_limit

    for entry in results:
        ip = entry.get("ip")
        if not ip:
            continue
        status: Dict[str, object] = {
            "host": ip,
            "timestamp": _now(),
            "reachable": bool(entry.get("reachable")),
        }
        if entry.get("port") is not None:
            status["port"] = entry.get("port")
        latency_value = entry.get("latency_ms")
        if isinstance(latency_value, (int, float)):
            status["latency_ms"] = float(latency_value)
        if entry.get("hostname"):
            status["hostname"] = entry.get("hostname")
        if slow_lookup and ip in slow_lookup:
            status["latency_warning"] = True
        if recovered_lookup and ip in recovered_lookup:
            status["recovered"] = True
        if flapping_lookup and ip in flapping_lookup:
            status["flapping"] = True
        change_info = change_lookup.get(ip)
        if change_info:
            status["port_changed"] = True
            if change_info.get("previous_port") is not None:
                status["previous_port"] = change_info.get("previous_port")
            if change_info.get("current_port") is not None:
                status.setdefault("port", change_info.get("current_port"))
                status["current_port"] = change_info.get("current_port")
        if history_limit_value is not None:
            status["port_change_history_limit"] = history_limit_value
        statuses.append(status)

    if not statuses:
        return

    try:
        node_control.record_statuses(statuses, max_entries=max_entries)
        if hasattr(node_control, "update_health"):
            node_control.update_health(statuses)
    except Exception:
        # Recording node status should never break discovery; failures are tolerated silently.
        pass


def _parse_positive_int(config: Dict[str, object], key: str) -> int | None:
    try:
        value = int(config.get(key, 0))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _parse_positive_float(
    config: Dict[str, object], key: str, *, default: float | None = None
) -> float | None:
    try:
        value = float(config.get(key, default if default is not None else 0.0))
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return value


def _coerce_ports(raw_ports) -> List[int]:
    ports: List[int] = []
    if isinstance(raw_ports, (list, tuple, set)):
        iterator = raw_ports
    else:
        iterator = [raw_ports]
    for item in iterator:
        try:
            port = int(item)
        except (TypeError, ValueError):
            continue
        if 0 < port < 65536:
            ports.append(port)
    if not ports:
        return [22, 80]
    return ports


if __name__ == "__main__":
    discover_from_config()
