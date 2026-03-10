from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "security" / "imp-cyber-researcher.py"
LOG = ROOT / "logs" / "imp-cyber-research.json"

spec = importlib.util.spec_from_file_location("cyber", MOD)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

module.run_cycle(sleep_ratio=0)

assert LOG.exists(), "Cyber research log missing"
with open(LOG) as f:
    data = json.load(f)
assert data, "Research cycle not recorded"
print("Cyber Researcher Test Passed!")
