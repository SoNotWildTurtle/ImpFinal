from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'core' / 'imp-tone-analyzer.py'

spec = importlib.util.spec_from_file_location('tone', SCRIPT)
tone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tone)

print('Testing Tone Analyzer...')
res1 = tone.analyze_tone('I am very happy today', speaker='alice')
assert res1['tone'] == 'positive'
assert res1['identity_verified'] is True
res2 = tone.analyze_tone('This is terrible', speaker='alice')
assert res2['tone'] == 'negative'
assert res2['identity_verified'] is False
print('Tone Analyzer Test Passed!')
