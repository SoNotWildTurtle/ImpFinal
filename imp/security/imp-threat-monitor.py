import subprocess
import json
import os
from pathlib import Path

THREAT_LOG = Path(__file__).resolve().parents[1] / "logs" / "imp-threat-log.json"


def detect_intrusions():

    print("Scanning system logs for threats...")

    if os.name == "nt":
        print("Windows detected. Skipping Linux auth-log intrusion checks.")
        return


    # Check for brute-force SSH attacks

    ssh_attempts_raw = subprocess.run(
        "grep 'Failed password' /var/log/auth.log | wc -l",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    suspicious_processes_raw = subprocess.run(
        "ps aux | grep -E 'nc|nmap|hydra|medusa|john|sqlmap' | grep -v grep | wc -l",
        shell=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    try:
        ssh_attempts = int(ssh_attempts_raw or "0")
    except ValueError:
        ssh_attempts = 0
    try:
        suspicious_processes = int(suspicious_processes_raw or "0")
    except ValueError:
        suspicious_processes = 0

    threats = {}



    if ssh_attempts > 10:

        threats["SSH Brute Force"] = f"{ssh_attempts} failed attempts detected"



    if suspicious_processes > 0:

        threats["Suspicious Processes"] = f"{suspicious_processes} known attack tools running"



    if threats:

        with open(THREAT_LOG, "w") as f:

            json.dump(threats, f, indent=4)



        print(f"THREAT DETECTED: {threats}")

if __name__ == "__main__":
    THREAT_LOG.parent.mkdir(parents=True, exist_ok=True)
    detect_intrusions()
