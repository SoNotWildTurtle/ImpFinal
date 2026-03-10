from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'core' / 'imp-speech-to-text.py'

print('Testing Speech-to-Text...')
subprocess.run([sys.executable, str(SCRIPT), "--check", "--offline"], check=False)
print('Speech-to-Text Test Executed!')
