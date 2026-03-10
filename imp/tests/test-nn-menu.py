import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "core" / "imp-nn-menu.py"

print("Checking neural manager CLI...")
output = subprocess.check_output([sys.executable, str(SCRIPT), "--register-basic", "--list"], text=True)
assert "basic" in output
print("Neural manager CLI Test Passed!")
