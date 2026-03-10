from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'expansion' / 'imp-distributed-queue.py'
LOG = ROOT / 'logs' / 'imp-distributed-queue.json'

spec = importlib.util.spec_from_file_location('dq', MODULE)
dq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dq)

print('Testing Distributed Queue...')
LOG.write_text('[]')

# add task
dq.add_task('echo hello')
assert json.loads(LOG.read_text())[0]['command'] == 'echo hello'

# ensure_task should not duplicate existing entries
dq.ensure_task('echo hello')
queue = json.loads(LOG.read_text())
assert sum(1 for item in queue if item['command'] == 'echo hello') == 1
dq.ensure_task('echo goodbye')
queue = json.loads(LOG.read_text())
assert any(item['command'] == 'echo goodbye' for item in queue)

# assign to node
assign = dq.assign_tasks(['localhost'])
assert 'localhost' in assign

# Capacity-aware assignment should bias towards weighted nodes without duplicating tasks endlessly.
LOG.write_text('[]')
for cmd in ['cmd1', 'cmd2', 'cmd3', 'cmd4']:
    dq.ensure_task(cmd)
assign_capacity = dq.assign_tasks(['node-a', 'node-b'], capacities={'node-a': 3, 'node-b': 1})
assert 'node-a' in assign_capacity
assert len(assign_capacity['node-a']) >= len(assign_capacity.get('node-b', []))

print('Distributed Queue Test Passed!')
