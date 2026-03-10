from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "self-improvement" / "imp-code-map.py"
LOG = ROOT / "logs" / "imp-code-map.json"
ANALYSIS_LOG = ROOT / "logs" / "imp-code-map-analysis.json"

spec = importlib.util.spec_from_file_location("code_map", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

print("Generating code map...")
path = module.generate_code_map()
analysis_path = module.analyze_code_map(path)

assert path == LOG and path.exists(), "Code map log missing"
with open(path, "r") as f:
    data = json.load(f)
    entry = data.get("imp/core/imp-execute.py")
    assert entry and "imports" in entry and "variables" in entry, "Missing imports/variables"
    assert "pathlib" in entry["imports"], "pathlib import missing"
    assert "ROOT" in entry["variables"], "ROOT variable missing"
print("Code Map Test Passed!")

with open(analysis_path, "r") as f:
    analysis = json.load(f)
    vuln = analysis.get("imp/security/imp-vulnerability-scanner.py")
    assert vuln and vuln.get("missing_test"), "Missing test not flagged"
    communicator_entry = analysis.get("imp/expansion/imp-node-communicator.py")
    assert not communicator_entry or not communicator_entry.get(
        "missing_test"
    ), "Node communicator test should be detected"
print("Code Map Analysis Test Passed!")
