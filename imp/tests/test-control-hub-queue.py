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


def test_queue_filters_and_pause():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        config = temp / "imp-control-policies.json"
        log = temp / "imp-control-hub.json"
        queue = temp / "imp-control-queue.json"
        history = temp / "imp-control-history.json"
        config.write_text("{}")
        hub = module.ControlHub(
            config_path=config,
            log_path=log,
            queue_path=queue,
            history_path=history,
        )
        plan = hub.build_plan("general.review")
        submission = hub.submit_plan(plan)
        assert submission["status"] == "pending"

        pending = hub.list_plans(status="pending")
        assert any(entry["id"] == submission["id"] for entry in pending)

        hub.pause_all("maintenance")
        events = hub.latest_events(limit=5)
        assert any(entry.get("event") == "pause_all" for entry in events)
