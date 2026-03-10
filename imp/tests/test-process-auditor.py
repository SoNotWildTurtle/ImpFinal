from pathlib import Path
import importlib.util
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
module_path = ROOT / 'security' / 'imp-process-auditor.py'
spec = importlib.util.spec_from_file_location('process_auditor', module_path)
process_auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(process_auditor)


def _fake_process(pid, name, cmdline, exe=''):
    info = {
        'pid': pid,
        'name': name,
        'cmdline': cmdline,
        'exe': exe,
    }
    return SimpleNamespace(info=info)


def run_test():
    temp_log = ROOT / 'logs' / 'test-process-audit.json'
    if temp_log.exists():
        temp_log.unlink()
    process_auditor.AUDIT_LOG = temp_log
    process_auditor.SUSPICIOUS_KEYWORDS = {'ncat'}

    fake_proc = _fake_process(1234, 'ncat', ['ncat', '-l', '9000'])
    process_auditor.psutil = SimpleNamespace(process_iter=lambda attrs=None: [fake_proc])

    entry = process_auditor.audit_processes()
    assert entry['suspicious_count'] == 1
    assert temp_log.exists()
    data = temp_log.read_text()
    assert 'ncat' in data

    temp_log.unlink()


if __name__ == '__main__':
    run_test()
