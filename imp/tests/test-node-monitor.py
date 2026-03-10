from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'expansion' / 'imp-node-monitor.py'

spec = importlib.util.spec_from_file_location('nm', MODULE_PATH)
nm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nm)

print('Testing Node Monitor...')
# Patch read_json to return sample nodes
nm.read_json = lambda *args, **kwargs: ['example.com', 'offline.test']
# Patch ping helper to control responses
nm._ping_host = lambda host: host == 'example.com'
# Capture output of write_json
written = {}
def fake_write(path, data):
    written['data'] = data
nm.write_json = fake_write

nm.check_node_health()
assert written['data'] == {'example.com': 'Online', 'offline.test': 'Offline'}
print('Node Monitor Test Passed')
