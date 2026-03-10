from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_network_auditor():
    print("Running Network Auditor...")
    script = ROOT / 'security' / 'imp-network-auditor.py'
    subprocess.run([sys.executable, str(script)])
    assert (ROOT / 'logs' / 'imp-network-audit.json').exists()
    print("Network Auditor Executed!")

if __name__ == '__main__':
    test_network_auditor()
