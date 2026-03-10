import os
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("imp_utils", ROOT / "core" / "imp_utils.py")
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
write_json = utils.write_json

STATUS_FILE = ROOT / "logs" / "imp-status.json"

def log_status():
    system_status = {
        "CPU Usage (%)": os.popen("grep 'cpu ' /proc/stat").read().strip(),
        "Memory Usage (%)": os.popen("free -m").read().strip(),
        "Uptime": os.popen("uptime -p").read().strip(),
    }

    write_json(STATUS_FILE, system_status)

    print("[+] System status logged.")


if __name__ == "__main__":
    log_status()
