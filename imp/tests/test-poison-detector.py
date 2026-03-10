from pathlib import Path
import importlib.util
from io import StringIO
import contextlib

ROOT = Path(__file__).resolve().parents[1]
poison_path = ROOT / 'security' / 'imp-poison-detector.py'
spec = importlib.util.spec_from_file_location('pd', poison_path)
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)

# use temporary files so we don't disturb real logs
test_learning = ROOT / 'logs' / 'test-learning.json'
test_goals = ROOT / 'logs' / 'test-goals.json'
test_log = ROOT / 'logs' / 'test-poison-log.json'
pd.LEARNING_DATA = test_learning
pd.POISON_LOG = test_log
pd.CRITICAL_FILES = {
    'learning_data': test_learning,
    'goals': test_goals,
}
try:
    test_learning.write_text('clean')
    test_goals.write_text('clean')
    buf1 = StringIO()
    with contextlib.redirect_stdout(buf1):
        pd.detect_poisoning()
    out1 = buf1.getvalue()
    assert 'checksum stable' in out1

    test_learning.write_text('tampered')
    buf2 = StringIO()
    with contextlib.redirect_stdout(buf2):
        pd.detect_poisoning()
    out2 = buf2.getvalue()
    assert 'Possible poisoning detected' in out2
finally:
    for p in [test_learning, test_goals, test_log]:
        if p.exists():
            p.unlink()
