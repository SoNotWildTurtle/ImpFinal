from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_network_monitor():
    print("Running Network Monitor...")
    script = ROOT / 'security' / 'imp-network-monitor.py'
    subprocess.run([sys.executable, str(script)])
    assert (ROOT / 'logs' / 'imp-network-baseline.json').exists()
    assert (ROOT / 'logs' / 'imp-network-diff.json').exists()
    print("Network Monitor Executed!")

if __name__ == '__main__':
    test_network_monitor()
