import json

def test_session_guard(tmp_path):
    from imp.security import imp_session_guard as session_guard

    config = {
        "max_session_minutes": 60,
        "max_idle_minutes": 15,
        "idle_lock_minutes": 5,
        "require_mfa": True,
        "allowed_origins": ["local"],
        "allowed_networks": ["127.0.0.1/32"],
        "flagged_roles": ["guest"],
        "risk_thresholds": {"high": 60, "medium": 30},
        "record_history": 5,
        "enable_origin_checks": True,
        "enable_idle_lock": True,
        "block_on_threat": True,
    }

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    now = "2025-01-01T12:00:00Z"
    sessions = [
        {
            "session_id": "safe",
            "user": "alex",
            "role": "owner",
            "origin": "local",
            "origin_ip": "127.0.0.1",
            "mfa": True,
            "started_at": "2025-01-01T11:30:00Z",
            "last_seen": "2025-01-01T11:55:00Z",
        },
        {
            "session_id": "risky",
            "user": "guest",
            "role": "guest",
            "origin": "external",
            "origin_ip": "203.0.113.1",
            "mfa": False,
            "started_at": "2024-12-31T23:00:00Z",
            "last_seen": "2025-01-01T10:00:00Z",
            "anomalies": ["token reuse"],
            "geo_anomaly": True,
        },
    ]

    auth_log = tmp_path / "auth.json"
    auth_log.write_text(json.dumps(sessions), encoding="utf-8")

    threat_log = tmp_path / "threat.json"
    threat_log.write_text(json.dumps([{"host": "risky"}]), encoding="utf-8")

    session_log = tmp_path / "session-log.json"

    # Patch _now to return deterministic timestamp
    original_now = session_guard._now
    session_guard._now = lambda: session_guard._parse_ts(now)
    try:
        summary = session_guard.evaluate_sessions(config_path, auth_log, session_log, threat_log)
    finally:
        session_guard._now = original_now

    assert summary["totals"]["high"] == 1
    assert summary["totals"]["medium"] == 0
    assert summary["totals"]["low"] == 1
    assert summary["flagged"][0]["session_id"] == "risky"
    assert "token reuse" in " ".join(summary["flagged"][0]["reasons"])
    assert summary["threat_hosts"] == ["risky"]

    history = json.loads(session_log.read_text(encoding="utf-8"))
    assert len(history) == 1
    assert history[0]["totals"] == summary["totals"]
