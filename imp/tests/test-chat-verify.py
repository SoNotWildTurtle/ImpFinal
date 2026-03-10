import subprocess
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
script = ROOT / 'bin' / 'imp-verify-chat.sh'
log = ROOT / 'logs' / 'imp-chat-keepalive.log'

# remove existing log to ensure test checks fresh output
if log.exists():
    log.unlink()

subprocess.run([str(script), '--no-start'], check=True)
assert log.exists(), 'keepalive log not created'

print('Chat verify test passed')
