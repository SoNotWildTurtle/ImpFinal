from pathlib import Path
import importlib.util
from io import StringIO
import contextlib

ROOT = Path(__file__).resolve().parents[1]


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_enforce_firewall():
    mod = _load_module('imp_firewall_manager', ROOT / 'security' / 'imp-firewall-manager.py')
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        mod.enforce_firewall()
    out = buf.getvalue()
    assert 'ufw command not found' in out or '[+] Firewall rules enforced.' in out
    print('Firewall manager executed')


if __name__ == '__main__':
    test_enforce_firewall()
