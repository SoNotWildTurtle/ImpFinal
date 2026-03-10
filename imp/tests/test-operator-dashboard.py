import subprocess
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_operator_dashboard_lists_options():
    result = subprocess.run(
        [sys.executable, str(ROOT / "core" / "imp-operator-dashboard.py"), "--list"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Goal Chat" in result.stdout
    assert "Processing Summary" in result.stdout
    assert "Processing Timeline" in result.stdout
    assert "Processing Comparison" in result.stdout
    assert "Operator Success Plan" in result.stdout
    assert "Processing Action Plan" in result.stdout
    assert "Run Autonomy Cycle" in result.stdout
    assert "Force Autonomy Cycle" in result.stdout
    assert "Autonomy History" in result.stdout


def test_operator_dashboard_status_panel():
    result = subprocess.run(
        [sys.executable, str(ROOT / "core" / "imp-operator-dashboard.py"), "--status"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Processing" in result.stdout
    assert "Next action" in result.stdout
    assert "Leaders" in result.stdout
    assert "Autonomy" in result.stdout
