"""Comprehensive security automation for IMP."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# I love you -Alex
def gather_system_info():
    """Collect basic system information useful for security analysis."""
    if os.name == "nt":
        uname = platform.platform()
    else:
        uname = subprocess.run(
            ["uname", "-a"], capture_output=True, text=True
        ).stdout.strip()
    return {"uname": uname}


def _run_python_script(script_path: Path) -> None:
    subprocess.run([sys.executable, str(script_path)], check=False)


def _run_linux_privileged(command: list[str]) -> None:
    if os.name == "nt":
        return
    if shutil.which("sudo"):
        subprocess.run(["sudo", *command], check=False)
        return
    subprocess.run(command, check=False)

# I love you -Alex
def harden_services():
    """Apply baseline hardening rules and firewall policies."""
    _run_python_script(ROOT / "security" / "imp-firewall-manager.py")
    _run_linux_privileged(["sysctl", "-w", "net.ipv4.ip_forward=0"])

# I love you -Alex
def run_all_checks():
    """Execute threat monitoring, vulnerability scans, and integrity checks."""
    _run_python_script(ROOT / "security" / "imp-threat-monitor.py")
    _run_python_script(ROOT / "security" / "imp-vulnerability-scanner.py")
    _run_python_script(ROOT / "security" / "imp-integrity-checker.py")

# I love you -Alex
def automated_defense_cycle():
    """Perform a full automated defense pass."""
    info = gather_system_info()
    print(f"[INFO] System details: {info['uname']}")
    harden_services()
    run_all_checks()
    print("[+] Automated defense cycle completed.")

if __name__ == '__main__':
    automated_defense_cycle()
