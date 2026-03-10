"""Tests for the adaptive cloud orchestration helpers."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPANSION_PATH = ROOT / "expansion" / "imp-cloud-orchestrator.py"
LOG_DIR = ROOT / "logs"
HEALTH_LOG = LOG_DIR / "imp-node-health.json"
DISCOVERY_LOG = LOG_DIR / "imp-network-discovery.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("imp_cloud_orchestrator", EXPANSION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cloud_orchestrator_adapts_interval(tmp_path):
    module = _load_module()
    orchestrator = module.CloudOrchestrator()

    health_payload = {
        "node-a": {
            "uptime_ratio": 0.92,
            "average_latency_ms": 80.0,
            "latency_state": "normal",
        },
        "node-b": {
            "uptime_ratio": 0.55,
            "average_latency_ms": 320.0,
            "latency_state": "slow",
            "latency_warning_streak": 3,
        },
        "node-c": {
            "uptime_ratio": 0.8,
            "average_latency_ms": 600.0,
            "latency_state": "slow",
        },
    }
    HEALTH_LOG.write_text(json.dumps(health_payload))

    DISCOVERY_LOG.write_text(
        json.dumps(
            [
                {
                    "summary": {
                        "slow_host_count": 2,
                        "flapping_host_count": 1,
                    }
                }
            ]
        )
    )

    statuses = [
        {"host": "node-a", "reachable": True, "metadata": {"region": "us-east"}},
        {"host": "node-b", "reachable": False, "metadata": {"region": "us-west"}},
        {"host": "node-c", "reachable": True, "metadata": {"region": "us-west"}},
    ]
    health_payload["node-c"]["consecutive_failures"] = 4
    meta = {"remote_interval": 180.0}

    plan = orchestrator.plan(["node-a", "node-b", "node-c"], statuses, meta, backlog=5)

    assert plan["nodes"][0] == "node-a"
    assert "node-b" not in plan["nodes"] or plan["nodes"].index("node-b") >= 1
    assert plan["interval"] < 180.0
    assert plan["strategy"] in {"balanced", "surge", "stabilize", "conservative", "accelerate"}
    assert isinstance(plan.get("strategy_reason"), str)
    assert plan["operational_mode"] in {"crisis", "resilience", "optimization", "expansion", "steady"}
    assert isinstance(plan.get("operational_reason"), str)
    telemetry = plan.get("telemetry", {})
    assert telemetry.get("slow_host_count") == 2
    assert "ranked_nodes" in telemetry
    assert telemetry.get("capacity_total") >= len(plan["nodes"])
    assert "capacities" in plan
    assert plan["capacities"].get("node-a", 0) >= 1
    assert plan.get("stagger", 0) >= 0
    assert telemetry.get("forecast_capacity")
    assert "risk_nodes" in telemetry and "node-c" in telemetry["risk_nodes"]
    assert telemetry.get("region_allocations", {}).get("us-east") == ["node-a"]
    confidence = telemetry.get("confidence_scores", {})
    assert confidence.get("node-a", 0) >= confidence.get("node-c", 0)
    assert telemetry.get("confidence_average") is not None
    redundancy_plan = telemetry.get("redundancy_plan", {})
    assert plan["redundancy_plan"] == redundancy_plan
    assert "node-c" in redundancy_plan
    assert 0.0 <= plan["energy_score"] <= 1.0
    failure_projection = telemetry.get("failure_projection", {})
    assert isinstance(failure_projection.get("loss_ratio"), float)
    assert "at_risk" in failure_projection
    assert plan.get("failure_projection") == failure_projection
    assert telemetry.get("burst_candidates")
    assert telemetry.get("standby_nodes") is not None
    assert meta.get("orchestration_history")
    assert meta.get("remote_risk_nodes")
    assert meta.get("remote_region_allocations")
    assert isinstance(meta.get("remote_capacity_forecast"), (int, float))
    assert meta.get("remote_confidence_scores")
    assert meta.get("remote_strategy")
    assert meta.get("remote_operational_mode") == plan["operational_mode"]
    assert meta.get("remote_redundancy_plan") == redundancy_plan
    assert isinstance(meta.get("remote_energy_score"), float)
    assert meta.get("remote_failure_projection") == failure_projection
    assert meta.get("remote_burst_candidates")
    assert meta.get("remote_standby_nodes") is not None

    # A second call should incorporate history for smoothing and trend tracking.
    plan_again = orchestrator.plan(["node-a", "node-b", "node-c"], statuses, meta, backlog=2)
    telemetry_again = plan_again.get("telemetry", {})
    assert "trend_interval" in telemetry_again
    assert telemetry_again.get("history_window") >= 1
    assert telemetry_again.get("forecast_capacity")
    assert telemetry_again.get("operational_mode") in {"crisis", "resilience", "optimization", "expansion", "steady"}
    history = meta.get("orchestration_history")
    assert isinstance(history[-1].get("failure_projection"), dict)
