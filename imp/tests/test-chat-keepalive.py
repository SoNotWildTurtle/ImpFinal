import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / 'bin' / 'imp-chat-keepalive.sh'
log = ROOT / 'logs' / 'imp-chat-keepalive.log'

if log.exists():
    log.unlink()

proc = subprocess.Popen([str(script)])
time.sleep(1)
proc.terminate()
proc.wait()
assert log.exists(), 'keepalive loop did not invoke verify script'

print('Chat keepalive test passed')
