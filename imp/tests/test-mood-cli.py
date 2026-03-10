from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'core' / 'imp-mood-manager.py'

print('Testing Mood CLI...')
result = subprocess.run([sys.executable, str(SCRIPT), '--get'], capture_output=True, text=True)
assert result.returncode == 0
print('Mood CLI Test Executed!')
