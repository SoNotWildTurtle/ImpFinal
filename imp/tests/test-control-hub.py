import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("imp.core.imp_control_hub", ROOT / "core" / "imp-control-hub.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
ControlHub = module.ControlHub


def test_control_hub_plan_generation(tmp_path):
    config = tmp_path / "config.json"
    log = tmp_path / "log.json"
    queue = tmp_path / "queue.json"
    history = tmp_path / "history.json"
    hub = ControlHub(config_path=config, log_path=log, queue_path=queue, history_path=history)

    hub.register_capability("example_tool", "Example capability", "system")
    hub.register_agent(
        "ops-agent",
        scope="system",
        endpoint="ssh://ops",
        capabilities=["example_tool"],
    )
    assert any(cap["name"] == "example_tool" for cap in hub.list_capabilities())
    assert any(agent["name"] == "ops-agent" for agent in hub.list_agents())

    details = hub.capability_details("example_tool")
    assert details and details["name"] == "example_tool"
    assert details["agents"] and details["agents"][0]["name"] == "ops-agent"

    plan = hub.build_plan("Please run an SSL check on staging", targets=["staging"], metadata={"risk_score": 0.3})
    assert plan["intent"] == "security.ssl_check"
    assert plan["targets"] == ["staging"]
    assert len(plan["steps"]) >= 3
    assert "audit_log" in plan["policy"]["requirements"]

    submission = hub.submit_plan(plan, metadata={"risk_score": 0.3})
    assert submission["status"] == "pending"
    assert any(entry["id"] == submission["id"] for entry in hub.list_plans())
    history_entries = hub.list_history()
    assert history_entries and history_entries[-1]["id"] == submission["id"]
    assert history_entries[-1]["status"] == "pending"

    approved = hub.approve_plan(submission["id"])
    assert approved
    approved_entries = hub.list_plans(status="approved")
    assert approved_entries and approved_entries[0]["status"] == "approved"
    history_entries = hub.list_history()
    assert history_entries[-1]["status"] == "approved"
    assert history_entries[-1]["approved_at"] > history_entries[-1]["submitted_at"]

    hub.pause_all("maintenance")
    events = hub.latest_events()
    assert events[-1]["event"] in {"pause_all", "plan_approved"}
    assert Path(config).exists()
    assert Path(queue).exists()
    assert Path(history).exists()


def test_control_hub_policy_denies_on_risk(tmp_path):
    config = tmp_path / "config.json"
    log = tmp_path / "log.json"
    queue = tmp_path / "queue.json"
    history = tmp_path / "history.json"
    hub = ControlHub(config_path=config, log_path=log, queue_path=queue, history_path=history)

    plan = hub.build_plan("Run system patch", metadata={"risk_score": 0.95})
    assert plan["policy"]["denied"]
