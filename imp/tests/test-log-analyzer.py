from pathlib import Path
import importlib.util
from types import SimpleNamespace
from unittest.mock import patch
import json

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_log_analyzer_creates_report():
    module = _load_module('imp_log_analyzer', ROOT / 'security' / 'imp-log-analyzer.py')
    report = ROOT / 'logs' / 'imp-log-analysis.json'
    if report.exists():
        report.unlink()
    fake_runs = [SimpleNamespace(stdout='12\n'), SimpleNamespace(stdout='6\n')]
    with patch('subprocess.run', side_effect=fake_runs):
        module.analyze_logs()
    assert report.exists()
    with report.open() as f:
        data = json.load(f)
    assert 'Excessive Failed Logins' in data


if __name__ == '__main__':
    test_log_analyzer_creates_report()
