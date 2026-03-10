from pathlib import Path
import ast
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'self-improvement' / 'imp-code-updater.py'

print('Checking Code Updater helpers...')
source = MODULE_PATH.read_text()
module = ast.parse(source)
funcs = {node.name for node in module.body if isinstance(node, ast.FunctionDef)}
assert 'decide_mode' in funcs, 'decide_mode function missing'
assert 'get_generator' in funcs, 'get_generator function missing'
assert 'is_placeholder_response' in funcs, 'placeholder check missing'

spec = importlib.util.spec_from_file_location('updater', MODULE_PATH)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
assert updater.is_placeholder_response('insert minimal python code here'), 'placeholder detection failed'
print('Code Updater Helper Test Passed!')
