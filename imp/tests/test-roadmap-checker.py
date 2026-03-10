import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / 'self-improvement' / 'imp-roadmap-checker.py'
LOG = ROOT / 'logs' / 'imp-roadmap-progress.json'
HISTORY_LOG = ROOT / 'logs' / 'imp-roadmap-progress-history.json'

spec = importlib.util.spec_from_file_location('roadmap_checker', CHECKER_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _load_history(path: Path):
    if path.exists():
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
        assert isinstance(data, list)
        return data
    return []


def test_roadmap_checker():
    history_before = _load_history(HISTORY_LOG)

    data = module.check_progress()

    assert LOG.exists()
    assert isinstance(data, dict)

    with open(LOG, encoding='utf-8') as handle:
        saved = json.load(handle)

    assert saved == data

    goals = saved.get(module.GOALS_KEY)
    summary = saved.get(module.SUMMARY_KEY)
    directories = saved.get(module.DIRECTORY_KEY)

    assert isinstance(goals, dict)
    assert goals
    assert isinstance(summary, dict)
    assert isinstance(directories, dict)

    checked_at = summary.get('checked_at')
    assert isinstance(checked_at, str)
    assert checked_at.endswith('Z')

    assert summary.get('modules_total', 0) >= summary.get('modules_completed', 0)

    history_after = _load_history(HISTORY_LOG)
    assert len(history_after) == len(history_before) + 1

    last_entry = history_after[-1]
    assert last_entry['timestamp'] == checked_at
    assert last_entry['modules_total'] == summary.get('modules_total')
    assert last_entry['modules_completed'] == summary.get('modules_completed')
    assert last_entry['modules_missing'] == summary.get('modules_missing')
    assert last_entry['missing_modules'] == sorted(
        module_name
        for modules in goals.values()
        for module_name, present in modules.items()
        if not present
    )
