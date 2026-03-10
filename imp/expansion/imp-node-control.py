"""Utilities for inspecting and recording cluster node status and assignments."""

from __future__ import annotations

import importlib.util
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = ROOT / "core"
CONFIG_DIR = ROOT / "config"
LOG_DIR = ROOT / "logs"

STATUS_LOG = LOG_DIR / "imp-node-status.json"
ASSIGNMENT_LOG = LOG_DIR / "imp-node-control.json"
HEALTH_LOG = LOG_DIR / "imp-node-health.json"
USAGE_LOG = LOG_DIR / "imp-node-usage.json"

MAX_LATENCY_HISTORY = 20
MAX_USAGE_HISTORY = 50
PORT_CHANGE_HISTORY_DEFAULT = 20
CLUSTER_NODES_FILE = CONFIG_DIR / "imp-cluster-nodes.json"


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


def _load_nodes() -> List[str]:
    return list(read_json(CLUSTER_NODES_FILE, []))


def resolve_nodes(nodes: Sequence[str] | None = None) -> List[Dict[str, object]]:
    """Attempt to resolve nodes to IP addresses and return status metadata."""

    hosts = list(nodes) if nodes is not None else _load_nodes()
    statuses: List[Dict[str, object]] = []
    for host in hosts:
        status: Dict[str, object] = {
            "host": host,
            "timestamp": _now(),
            "reachable": False,
        }
        try:
            _, _, ip_addresses = socket.gethostbyname_ex(host)
            status["reachable"] = bool(ip_addresses)
            status["addresses"] = ip_addresses
        except socket.gaierror:
            status["addresses"] = []
        statuses.append(status)
    return statuses


def record_statuses(
    statuses: Sequence[Dict[str, object]], *, max_entries: int | None = None
) -> None:
    """Append a status snapshot to the node status log."""

    if not statuses:
        return
    snapshot = {
        "timestamp": _now(),
        "statuses": list(statuses),
    }
    history = read_json(STATUS_LOG, [])
    history.append(snapshot)
    if max_entries and max_entries > 0 and len(history) > max_entries:
        history = history[-max_entries:]
    write_json(STATUS_LOG, history)


def record_usage(
    usage_snapshots: Sequence[Dict[str, object]], *, max_entries: int | None = None
) -> None:
    """Append usage telemetry to the node usage log."""

    if not usage_snapshots:
        return

    entry = {
        "timestamp": _now(),
        "snapshots": list(usage_snapshots),
    }
    history = read_json(USAGE_LOG, [])
    history.append(entry)
    if max_entries and max_entries > 0 and len(history) > max_entries:
        history = history[-max_entries:]
    write_json(USAGE_LOG, history)


def update_health(statuses: Sequence[Dict[str, object]]) -> None:
    """Update per-host health metadata for management dashboards."""

    if not statuses:
        return

    health = read_json(HEALTH_LOG, {})
    if not isinstance(health, dict):
        health = {}

    timestamp = _now()
    for status in statuses:
        host = status.get("host")
        if not host:
            continue

        entry = dict(health.get(host) or {})
        entry["last_seen"] = timestamp

        latency_value = status.get("latency_ms")
        latency_warning = bool(status.get("latency_warning"))

        history_limit_value = status.get("port_change_history_limit")
        if isinstance(history_limit_value, int) and history_limit_value > 0:
            port_history_limit = history_limit_value
        else:
            existing_limit = entry.get("port_change_history_limit")
            if isinstance(existing_limit, int) and existing_limit > 0:
                port_history_limit = existing_limit
            else:
                port_history_limit = PORT_CHANGE_HISTORY_DEFAULT
        entry["port_change_history_limit"] = port_history_limit
        port_history = list(entry.get("port_change_history", []))

        total_checks = int(entry.get("total_checks", 0)) + 1
        entry["total_checks"] = total_checks
        success_checks = int(entry.get("success_checks", 0))
        failure_checks = int(entry.get("failure_checks", 0))

        if status.get("reachable"):
            entry["state"] = "online"
            entry["consecutive_failures"] = 0
            entry["last_success"] = timestamp
            if status.get("port") is not None:
                entry["last_port"] = status.get("port")
            if latency_value is not None:
                entry["last_latency_ms"] = float(latency_value)
            success_checks += 1
        else:
            entry["state"] = "offline"
            entry["consecutive_failures"] = int(entry.get("consecutive_failures", 0)) + 1
            failure_checks += 1

        if status.get("hostname"):
            entry["hostname"] = status.get("hostname")

        if latency_value is not None:
            history = list(entry.get("latency_history", []))
            history.append({"timestamp": timestamp, "latency_ms": float(latency_value)})
            entry["latency_history"] = history[-MAX_LATENCY_HISTORY:]
            numeric_samples = [
                sample.get("latency_ms")
                for sample in entry["latency_history"]
                if isinstance(sample.get("latency_ms"), (int, float))
            ]
            if numeric_samples:
                entry["average_latency_ms"] = sum(numeric_samples) / len(numeric_samples)

        if latency_warning:
            entry["latency_state"] = "slow"
            entry["last_latency_warning"] = timestamp
            entry["latency_warning_count"] = int(entry.get("latency_warning_count", 0)) + 1
            entry["latency_warning_streak"] = int(entry.get("latency_warning_streak", 0)) + 1
        elif status.get("reachable"):
            entry["latency_state"] = "normal"
            entry.pop("last_latency_warning", None)
            entry["latency_warning_streak"] = 0
        else:
            entry["latency_state"] = "offline"
            entry["latency_warning_streak"] = 0

        if status.get("recovered") and status.get("reachable"):
            entry["last_recovery"] = timestamp
            entry["recovery_count"] = int(entry.get("recovery_count", 0)) + 1

        flapping_flag = bool(status.get("flapping"))
        entry["flapping"] = flapping_flag
        if flapping_flag:
            entry["last_flap"] = timestamp
            entry["flap_count"] = int(entry.get("flap_count", 0)) + 1

        if status.get("port_changed"):
            entry["port_change_count"] = int(entry.get("port_change_count", 0)) + 1
            entry["last_port_change"] = timestamp
            if status.get("previous_port") is not None:
                entry["previous_port"] = status.get("previous_port")
            if status.get("current_port") is not None:
                entry["last_port"] = status.get("current_port")
            event = {"timestamp": timestamp}
            if status.get("previous_port") is not None:
                event["previous_port"] = status.get("previous_port")
            if status.get("current_port") is not None:
                event["current_port"] = status.get("current_port")
            port_history.append(event)

        if port_history:
            limit = port_history_limit if port_history_limit > 0 else PORT_CHANGE_HISTORY_DEFAULT
            entry["port_change_history"] = port_history[-limit:]

        usage = status.get("usage")
        if isinstance(usage, dict):
            usage_entry = dict(entry.get("usage") or {})
            usage_history = dict(entry.get("usage_history") or {})

            for key in ("cpu_percent", "memory_percent", "gpu_percent", "disk_percent", "network_mbps"):
                value = usage.get(key)
                if isinstance(value, (int, float)):
                    usage_entry[key] = float(value)
                    samples = usage_history.get(key, [])
                    samples.append({"timestamp": timestamp, "value": float(value)})
                    usage_history[key] = samples[-MAX_USAGE_HISTORY:]

            tasks_value = usage.get("active_tasks")
            if isinstance(tasks_value, int):
                usage_entry["active_tasks"] = max(tasks_value, 0)

            entry["usage"] = usage_entry
            if usage_history:
                entry["usage_history"] = usage_history

        if isinstance(status.get("active_tasks"), int):
            entry.setdefault("usage", {})["active_tasks"] = max(status["active_tasks"], 0)

        entry["success_checks"] = success_checks
        entry["failure_checks"] = failure_checks
        if total_checks > 0:
            entry["uptime_ratio"] = success_checks / total_checks
        else:
            entry.pop("uptime_ratio", None)

        health[host] = entry

    write_json(HEALTH_LOG, health)


def usage_summary(
    *, thresholds: Dict[str, float] | None = None, health: Dict[str, object] | None = None
) -> Dict[str, object]:
    """Aggregate usage statistics from the health log or supplied data."""

    if health is None or not isinstance(health, dict):
        loaded = read_json(HEALTH_LOG, {})
        health = loaded if isinstance(loaded, dict) else {}

    thresholds = thresholds or {}
    aggregates = {
        "hosts": 0,
        "average_cpu_percent": 0.0,
        "average_memory_percent": 0.0,
        "average_gpu_percent": 0.0,
        "average_disk_percent": 0.0,
        "average_network_mbps": 0.0,
        "total_active_tasks": 0,
        "threshold_breaches": {},
    }

    totals = {
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "gpu_percent": 0.0,
        "disk_percent": 0.0,
        "network_mbps": 0.0,
    }
    counts = {metric: 0 for metric in totals}
    breaches: Dict[str, List[str]] = {metric: [] for metric in totals}

    for host, entry in health.items():
        usage = entry.get("usage")
        if not isinstance(usage, dict):
            continue

        aggregates["hosts"] += 1
        active_tasks = usage.get("active_tasks")
        if isinstance(active_tasks, int):
            aggregates["total_active_tasks"] += max(active_tasks, 0)

        for metric in totals:
            value = usage.get(metric)
            if isinstance(value, (int, float)):
                totals[metric] += float(value)
                counts[metric] += 1
                threshold = thresholds.get(metric)
                if isinstance(threshold, (int, float)) and float(value) >= float(threshold):
                    breaches[metric].append(host)

    for metric in totals:
        if counts[metric]:
            aggregates[f"average_{metric}"] = totals[metric] / counts[metric]
        if breaches[metric]:
            aggregates["threshold_breaches"][metric] = breaches[metric]

    return aggregates


def reachable_hosts(statuses: Sequence[Dict[str, object]]) -> List[str]:
    """Return the hosts that resolved successfully."""

    return [entry["host"] for entry in statuses if entry.get("reachable")]


def record_assignments(
    assignments: Dict[str, Iterable[str]],
    *,
    tasks: Sequence[str] | None = None,
    remote_dir: str | None = None,
) -> None:
    """Persist remote task assignments for later inspection."""

    if not assignments:
        return
    entry = {
        "timestamp": _now(),
        "assignments": {host: list(cmds) for host, cmds in assignments.items()},
        "tasks": list(tasks or []),
        "remote_dir": remote_dir,
    }
    history = read_json(ASSIGNMENT_LOG, [])
    history.append(entry)
    write_json(ASSIGNMENT_LOG, history)


__all__ = [
    "ASSIGNMENT_LOG",
    "HEALTH_LOG",
    "USAGE_LOG",
    "STATUS_LOG",
    "record_assignments",
    "record_statuses",
    "record_usage",
    "update_health",
    "usage_summary",
    "reachable_hosts",
    "resolve_nodes",
]

