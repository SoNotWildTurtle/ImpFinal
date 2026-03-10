from pathlib import Path
SCRIPT = Path(__file__).resolve().parents[1] / 'bin' / 'imp-auto-heal-run.sh'
print('Checking auto-heal runner...')
assert SCRIPT.exists() and SCRIPT.stat().st_mode & 0o111, 'imp-auto-heal-run.sh missing or not executable'
print('Auto-heal runner test passed!')
