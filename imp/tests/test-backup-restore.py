from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / 'bin' / 'imp-backup.sh'
RESTORE = ROOT / 'bin' / 'imp-restore.sh'

print('Checking Backup and Restore scripts...')
assert BACKUP.exists(), 'imp-backup.sh missing'
assert RESTORE.exists(), 'imp-restore.sh missing'
assert os.access(BACKUP, os.X_OK), 'imp-backup.sh not executable'
assert os.access(RESTORE, os.X_OK), 'imp-restore.sh not executable'
with open(BACKUP) as f:
    data = f.read()
    assert 'tar -czf' in data
    assert 'gpg --symmetric' in data
with open(RESTORE) as f:
    data = f.read()
    assert 'gpg --output' in data
    assert 'tar -xzf' in data
print('Backup and Restore scripts OK!')
