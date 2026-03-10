import importlib.util
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("imp_utils", ROOT / "core" / "imp_utils.py")
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
read_json = utils.read_json
write_json = utils.write_json

NODE_HEALTH_LOG = ROOT / "logs" / "imp-node-health.json"
CLUSTER_NODES_FILE = ROOT / "config" / "imp-cluster-nodes.json"

def _ping_command(host: str) -> list[str]:
    """Return a cross-platform ping command for *host*."""

    count_flag = "-n" if platform.system().lower().startswith("win") else "-c"
    return ["ping", count_flag, "1", host]


def _ping_host(host: str) -> bool:
    """Ping *host* and return True when reachable."""

    try:
        result = subprocess.run(
            _ping_command(host),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return result.returncode == 0


def check_node_health():
    nodes = read_json(CLUSTER_NODES_FILE, [])

    health_status = {}

    for node in nodes:
        health_status[node] = "Online" if _ping_host(node) else "Offline"

    write_json(NODE_HEALTH_LOG, health_status)

    print("[+] Node health check completed.")

if __name__ == "__main__":
    check_node_health()
