from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-processing-manager.py"

spec = importlib.util.spec_from_file_location("imp_processing_manager", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_register_groups_with_options():
    manager = module.ProcessingManager()
    spec_entry = ("demo", str(ROOT / "core" / "imp-learning-memory.py"), "store_learnings")
    mapping = {
        "group_a": [spec_entry],
        "group_b": {
            "specs": [spec_entry],
            "options": {"remote_interval": 123.0, "sync_cluster": True},
        },
    }
    manager.register_groups(mapping)
    assert "group_a" in manager.groups
    assert "group_b" in manager.groups
    assert manager.group_meta["group_b"]["remote_interval"] == 123.0
    assert manager.group_meta["group_b"]["sync_cluster"] is True
