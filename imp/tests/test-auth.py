from pathlib import Path
import subprocess
import json
import importlib.util
import time
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'security' / 'imp-authenticator.py'
CONFIG = ROOT / 'config' / 'imp-credentials.json'

with open(CONFIG) as f:
    data = json.load(f)
user = data['users'][0]['username']

print('Testing Authentication...')
subprocess.run([sys.executable, str(SCRIPT), "-u", user, "-p", "demo"], check=False, timeout=15)
subprocess.run([sys.executable, str(SCRIPT), "-g", "invalidtoken"], check=False, timeout=15)
if os.environ.get("IMP_RUN_INTERACTIVE_AUTH_TESTS") == "1":
    subprocess.run(
        [sys.executable, str(SCRIPT), "--google-auto", "--google-email", "test@example.com"],
        check=False,
        timeout=30,
    )
else:
    print("Skipping interactive Google OAuth auth test.")
spec = importlib.util.spec_from_file_location('imp_auth', SCRIPT)
imp_auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp_auth)
assert imp_auth.idle_relog(time.time())
original_google_auto = imp_auth.authenticate_google_auto
imp_auth.authenticate_google_auto = lambda email=None: False
assert not imp_auth.idle_relog(time.time() - 301)
imp_auth.authenticate_google_auto = original_google_auto
print('Authentication Test Executed!')
