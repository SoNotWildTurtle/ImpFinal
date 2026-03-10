from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'core' / 'imp-voice.py'

print('Testing Voice Synthesis...')
subprocess.run(
    [sys.executable, str(SCRIPT), "--voice-name", "female", "--rate", "150", "test phrase"],
    check=False,
)
print('Voice Synthesis Test Executed!')
