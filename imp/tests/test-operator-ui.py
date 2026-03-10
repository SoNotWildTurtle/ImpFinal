from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-operator-ui.py"

spec = importlib.util.spec_from_file_location("imp_operator_ui", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_status_payload_shape():
    payload = module._status_payload()
    assert "processing" in payload
    assert "autonomy" in payload
