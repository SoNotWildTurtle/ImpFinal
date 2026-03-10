"""Tests for node control utilities."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "expansion" / "imp-node-control.py"
spec = importlib.util.spec_from_file_location("imp_node_control", MODULE_PATH)
node_control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(node_control)


def _load(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return []


def _store(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)


def test_resolve_nodes_and_logs(tmp_path):
    status_log = node_control.STATUS_LOG
    assignment_log = node_control.ASSIGNMENT_LOG
    health_log = getattr(node_control, "HEALTH_LOG", None)
    usage_log = getattr(node_control, "USAGE_LOG", None)

    original_status = _load(status_log)
    original_assignment = _load(assignment_log)
    original_health = _load(health_log) if health_log else None
    original_usage = _load(usage_log) if usage_log else None
    try:
        statuses = node_control.resolve_nodes(["localhost"])
        assert statuses and statuses[0]["host"] == "localhost"

        node_control.record_statuses(statuses, max_entries=1)
        node_control.record_statuses(statuses, max_entries=1)
        updated_status = _load(status_log)
        assert updated_status
        assert len(updated_status) <= 1

        if usage_log:
            node_control.record_usage(
                [
                    {
                        "host": "localhost",
                        "usage": {"cpu_percent": 42.5, "memory_percent": 33.0, "active_tasks": 2},
                    }
                ],
                max_entries=2,
            )
            node_control.record_usage(
                [
                    {
                        "host": "localhost",
                        "usage": {"cpu_percent": 40.0, "memory_percent": 31.0, "active_tasks": 1},
                    }
                ],
                max_entries=2,
            )
            usage_history = _load(usage_log)
            assert usage_history and len(usage_history) <= 2

        node_control.record_assignments({"localhost": ["echo test"]}, tasks=["echo test"], remote_dir="/tmp")
        updated_assignment = _load(assignment_log)
        assert updated_assignment

        if health_log:
            node_control.update_health(statuses)
            health_data = _load(health_log)
            assert isinstance(health_data, dict)
            assert "localhost" in health_data
            assert health_data["localhost"]["state"] in {"online", "offline"}
            assert health_data["localhost"].get("latency_state") in {
                "normal",
                "slow",
                "offline",
                None,
            }
            assert health_data["localhost"].get("total_checks", 0) >= 1
            assert "uptime_ratio" in health_data["localhost"]

            node_control.update_health(
                [
                    {
                        "host": "usage.local",
                        "reachable": True,
                        "usage": {
                            "cpu_percent": 55.5,
                            "memory_percent": 44.0,
                            "gpu_percent": 25.0,
                            "disk_percent": 70.0,
                            "network_mbps": 120.0,
                            "active_tasks": 5,
                        },
                    }
                ]
            )
            usage_health = _load(health_log)
            assert usage_health["usage.local"]["usage"]["cpu_percent"] == 55.5
            assert usage_health["usage.local"].get("usage_history")
            summary = node_control.usage_summary(
                thresholds={"cpu_percent": 50.0, "memory_percent": 40.0},
                health=usage_health,
            )
            assert summary["hosts"] >= 1
            assert summary["average_cpu_percent"] >= 50.0
            assert "cpu_percent" in summary["threshold_breaches"]

            node_control.update_health(
                [
                    {
                        "host": "slow.local",
                        "reachable": True,
                        "latency_ms": 750.0,
                        "latency_warning": True,
                    }
                ]
            )
            slow_health = _load(health_log)
            assert slow_health["slow.local"]["latency_state"] == "slow"
            assert slow_health["slow.local"]["latency_history"]
            assert slow_health["slow.local"]["latency_warning_count"] >= 1
            assert slow_health["slow.local"].get("latency_warning_streak", 0) >= 1
            assert abs(slow_health["slow.local"].get("average_latency_ms", 0) - 750.0) < 1e-6

            node_control.update_health(
                [
                    {
                        "host": "offline.local",
                        "reachable": False,
                    }
                ]
            )
            offline_health = _load(health_log)
            assert offline_health["offline.local"]["failure_checks"] >= 1
            assert offline_health["offline.local"].get("uptime_ratio", 0.0) <= 0.0

            node_control.update_health(
                [
                    {
                        "host": "recover.local",
                        "reachable": True,
                        "recovered": True,
                    }
                ]
            )
            recovery_health = _load(health_log)
            assert recovery_health["recover.local"]["recovery_count"] >= 1
            assert recovery_health["recover.local"].get("last_recovery")

            node_control.update_health(
                [
                    {
                        "host": "flap.local",
                        "reachable": True,
                        "flapping": True,
                    }
                ]
            )
            flapping_health = _load(health_log)
            assert flapping_health["flap.local"].get("flapping") is True
            assert flapping_health["flap.local"].get("flap_count", 0) >= 1
            assert flapping_health["flap.local"].get("last_flap")

            node_control.update_health(
                [
                    {
                        "host": "port-change.local",
                        "reachable": True,
                        "port": 443,
                        "port_changed": True,
                        "previous_port": 22,
                        "current_port": 443,
                    }
                ]
            )
            port_change_health = _load(health_log)
            assert port_change_health["port-change.local"].get("port_change_count", 0) >= 1
            assert port_change_health["port-change.local"].get("last_port_change")
            assert port_change_health["port-change.local"].get("previous_port") == 22
            assert port_change_health["port-change.local"].get("last_port") == 443
            history = port_change_health["port-change.local"].get("port_change_history", [])
            assert history, "Port change history should capture events"
            assert history[-1].get("current_port") == 443
            assert len(history) <= node_control.PORT_CHANGE_HISTORY_DEFAULT
    finally:
        _store(status_log, original_status)
        _store(assignment_log, original_assignment)
        if health_log and original_health is not None:
            _store(health_log, original_health)
        if usage_log and original_usage is not None:
            _store(usage_log, original_usage)


def test_reachable_hosts_filters_only_resolved():
    statuses = [
        {"host": "localhost", "reachable": True},
        {"host": "invalid.example", "reachable": False},
    ]
    reachable = node_control.reachable_hosts(statuses)
    assert reachable == ["localhost"]

