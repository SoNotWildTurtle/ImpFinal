from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-processing-manager.py"

spec = importlib.util.spec_from_file_location("imp_processing_manager", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_validate_specs_detects_missing_path():
    manager = module.ProcessingManager()
    missing_path = ROOT / "core" / "does-not-exist.py"
    manager.register_group(
        "bad",
        [("missing", str(missing_path), "run")],
    )
    errors, invalid = manager.validate_specs()
    assert errors, "Expected validation errors"
    assert invalid, "Expected invalid spec tracking"
    assert errors[0]["error"] == "module_path_missing"
