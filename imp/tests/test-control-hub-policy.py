from pathlib import Path
import importlib.util
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-control-hub.py"

spec = importlib.util.spec_from_file_location("imp_control_hub", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_policy_transforms_and_approval():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        config = temp / "imp-control-policies.json"
        log = temp / "imp-control-hub.json"
        queue = temp / "imp-control-queue.json"
        history = temp / "imp-control-history.json"
        config.write_text(
            "{\n"
            "  \"policies\": [\n"
            "    {\n"
            "      \"name\": \"security_guard\",\n"
            "      \"match\": \"security.*\",\n"
            "      \"require\": [\"audit\"],\n"
            "      \"deny_if\": {\"risk_score\": 0.5},\n"
            "      \"transforms\": [\"preflight_health_check\", \"append_summary\"]\n"
            "    }\n"
            "  ]\n"
            "}\n"
        )
        hub = module.ControlHub(
            config_path=config,
            log_path=log,
            queue_path=queue,
            history_path=history,
        )
        plan = hub.build_plan("security.audit", metadata={"risk_score": 0.9})
        assert plan["policy"]["requirements"], "Expected policy requirements"
        assert "manual_override" in plan["policy"]["requirements"]
        assert plan["steps"][0] == "preflight_health_check"
        assert plan["steps"][-1] == "deliver_summary"

        submission = hub.submit_plan(plan)
        assert submission["status"] == "pending"
        approved = hub.approve_plan(submission["id"])
        assert approved
        history_entries = hub.list_history(limit=None)
        assert any(entry.get("status") == "approved" for entry in history_entries)
