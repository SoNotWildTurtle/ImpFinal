from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-execute.py"

spec = importlib.util.spec_from_file_location("imp_execute", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

def test_build_manager_groups():
    manager = module.build_manager(max_threads=2, max_cycles=1)
    groups = manager.groups
    assert "autonomy" in groups
    assert "knowledge" in groups
    assert "self_improvement" in groups
    assert "security" in groups
    assert "expansion" in groups
    for name, specs in groups.items():
        assert specs, f"Group {name} should have specs"
