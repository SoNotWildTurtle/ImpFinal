from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "security" / "imp-processing-security.py"

spec = importlib.util.spec_from_file_location("imp_processing_security", MODULE_PATH)
processing_security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(processing_security)


def test_processing_security_filters_nodes(tmp_path):
    config_path = ROOT / "config" / "imp-processing-security-test.json"
    cluster_path = ROOT / "config" / "imp-cluster-nodes-test.json"
    audit_path = ROOT / "logs" / "imp-network-audit-test.json"
    diff_path = ROOT / "logs" / "imp-network-diff-test.json"
    discovery_path = ROOT / "logs" / "imp-network-discovery-test.json"
    security_log = ROOT / "logs" / "imp-processing-security-test.json"
    health_log = ROOT / "logs" / "imp-node-health-test.json"
    intranet_path = ROOT / "config" / "imp-intranet-test.json"
    host_key_path = ROOT / "config" / "imp-host-keys-test.json"
    process_audit_path = ROOT / "logs" / "imp-process-audit-test.json"
    threat_log_path = ROOT / "logs" / "imp-threat-log-test.json"

    threat_log_path.write_text(json.dumps({}))

    config_path.write_text(json.dumps({
        "require_allowlist": True,
        "block_unreachable": True,
        "flag_new_or_unknown_hosts": True,
        "alert_on_audit_matches": True,
        "block_slow_hosts": True,
        "block_flapping_hosts": True,
        "block_recent_port_changes": True,
        "respect_orchestrator_risk": True,
        "max_latency_ms": 80,
        "allowed_networks": ["198.51.100.0/24"],
        "blocked_networks": ["203.0.113.0/24"],
        "allowed_ports": [22],
        "forbidden_ports": [23],
        "allowed_hostname_suffixes": [".internal"],
        "require_intranet_membership": True,
        "max_log_entries": 10,
        "block_latency_warnings": True,
        "max_latency_warning_streak": 1,
        "block_unhealthy_state": True,
        "max_consecutive_failures": 2,
        "require_host_keys": True,
        "block_host_key_mismatch": True,
        "host_keys_file": host_key_path.name,
        "block_process_audit_matches": True,
        "block_active_threats": True,
        "block_unmatched_threats": False,
        "threat_log_file": threat_log_path.name,
    }))
    cluster_path.write_text(json.dumps([
        "node-allowed.internal",
        "node-slow.internal",
        "node-port.internal"
    ]))
    audit_path.write_text(json.dumps([
        {"remote": "203.0.113.5:22"}
    ]))
    diff_path.write_text(json.dumps([
        {
            "new_hosts": ["198.51.100.7"],
            "slow_hosts": [],
            "flapping_hosts": [],
            "port_changes": [],
        }
    ]))
    discovery_path.write_text(json.dumps([
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "results": [
                {"ip": "198.51.100.5", "latency_ms": 95, "reachable": True, "port": 22},
                {"ip": "198.51.100.9", "latency_ms": 12, "reachable": True, "port": 22},
                {"ip": "198.51.100.12", "latency_ms": 15, "reachable": True, "port": 23},
                {"ip": "198.18.0.1", "latency_ms": 30, "reachable": True, "port": 80}
            ],
            "summary": {
                "slow_hosts": [
                    {"ip": "198.51.100.5", "latency_ms": 95, "port": 22}
                ],
                "flapping_hosts": [],
                "recovered_hosts": [],
                "port_changes": []
            }
        }
    ]))
    security_log.write_text("[]")
    health_log.write_text(json.dumps({
        "node-slow.internal": {
            "state": "online",
            "latency_state": "slow",
            "latency_warning_streak": 2,
        },
        "node-blocked": {
            "state": "offline",
            "consecutive_failures": 5,
        },
    }))
    intranet_path.write_text(json.dumps({
        "nodes": [
            "198.51.100.0/24",
            "node-allowed.internal",
            "node-slow.internal",
            "node-port.internal"
        ]
    }))
    host_key_path.write_text(json.dumps({
        "node-allowed.internal": "aa:bb:cc",
        "node-blocked": "dd:ee:ff",
    }))
    process_audit_path.write_text(json.dumps([
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "findings": [
                {"host": "node-blocked", "reasons": ["keyword:nc"]}
            ],
        }
    ]))

    # Rebind module constants to the test fixtures.
    processing_security.CONFIG_FILE = config_path
    processing_security.CLUSTER_NODES_FILE = cluster_path
    processing_security.AUDIT_LOG = audit_path
    processing_security.DIFF_LOG = diff_path
    processing_security.DISCOVERY_LOG = discovery_path
    processing_security.NODE_HEALTH_LOG = health_log
    processing_security.SECURITY_LOG = security_log
    processing_security.INTRANET_CONFIG = intranet_path
    processing_security.HOST_KEYS_FILE = host_key_path
    processing_security.PROCESS_AUDIT_LOG = process_audit_path
    processing_security.THREAT_LOG = threat_log_path

    statuses = [
        {"host": "node-allowed.internal", "reachable": True, "addresses": ["198.51.100.9"], "metadata": {"ssh_fingerprint": "aa:bb:cc"}},
        {"host": "node-blocked", "reachable": False, "addresses": ["203.0.113.5"], "metadata": {"ssh_fingerprint": "00:11:22"}},
        {"host": "198.51.100.7", "reachable": True, "addresses": ["198.51.100.7"]},
        {"host": "node-slow.internal", "reachable": True, "addresses": ["198.51.100.5"]},
        {"host": "node-port.internal", "reachable": True, "addresses": ["198.51.100.12"]},
        {"host": "node-external.example.com", "reachable": True, "addresses": ["198.18.0.1"]},
    ]

    assessment = processing_security.assess_processing_nodes(
        [
            "node-allowed.internal",
            "node-blocked",
            "198.51.100.7",
            "node-slow.internal",
            "node-port.internal",
            "node-external.example.com",
        ],
        statuses=statuses,
        meta={"group": "test"},
    )

    assert assessment["allowed_nodes"] == ["node-allowed.internal"]
    blocked = {item["host"]: item["issues"] for item in assessment["blocked_nodes"]}
    assert "node-blocked" in blocked
    assert "unreachable" in blocked["node-blocked"]
    assert "198.51.100.7" in blocked
    assert "network_diff_flag" in blocked["198.51.100.7"]
    assert any("network_audit_flag" in issues for issues in blocked.values())
    assert "node-slow.internal" in blocked and "slow_host" in blocked["node-slow.internal"]
    assert "latency_threshold" in blocked["node-slow.internal"]
    assert "latency_warning" in blocked["node-slow.internal"]
    assert "latency_warning_streak" in blocked["node-slow.internal"]
    assert "node-port.internal" in blocked
    assert "port_not_allowed" in blocked["node-port.internal"]
    assert "forbidden_port" in blocked["node-port.internal"]
    assert "node-external.example.com" in blocked
    assert "not_intranet_member" in blocked["node-external.example.com"]
    assert "hostname_policy_violation" in blocked["node-external.example.com"]
    assert "consecutive_failures" in blocked["node-blocked"]
    assert "unhealthy_state" in blocked["node-blocked"]
    assert "host_key_mismatch" in blocked["node-blocked"]
    assert "process_audit_flag" in blocked["node-blocked"]

    history = json.loads(security_log.read_text())
    assert history and history[-1]["blocked_nodes"], "Security log should record blocked nodes"
    summary = history[-1]
    assert summary.get("flagged_host_reasons")
    assert summary.get("health_matches")
    assert summary.get("host_key_policy")
    assert summary.get("discovery_metadata")

    # Introduce an active threat for a single host and ensure only that node is blocked.
    threat_log_path.write_text(json.dumps([
        {"type": "SSH Brute Force", "host": "node-blocked"}
    ]))
    assessment_with_threat = processing_security.assess_processing_nodes(
        [
            "node-allowed.internal",
            "node-blocked",
            "198.51.100.7",
            "node-slow.internal",
            "node-port.internal",
            "node-external.example.com",
        ],
        statuses=statuses,
    )

    blocked_again = {item["host"]: item["issues"] for item in assessment_with_threat["blocked_nodes"]}
    assert "node-blocked" in blocked_again and "active_threat" in blocked_again["node-blocked"]
    assert "node-allowed.internal" not in blocked_again
    assert assessment_with_threat.get("threat_host_matches", {}).get("node-blocked")
    assert assessment_with_threat.get("threats")
    assert assessment_with_threat.get("threat_blocking") is True

    # Enable global blocking and confirm unmatched threats pause execution.
    config = json.loads(config_path.read_text())
    config["block_unmatched_threats"] = True
    config_path.write_text(json.dumps(config))
    threat_log_path.write_text(json.dumps({"Global Alert": "investigate"}))
    assessment_global = processing_security.assess_processing_nodes(
        [
            "node-allowed.internal",
            "node-blocked",
        ],
        statuses=statuses,
    )
    assert not assessment_global["allowed_nodes"], "Global threats should block execution when enabled"
