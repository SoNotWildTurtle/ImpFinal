import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCE_LOG = ROOT / "logs" / "imp-resource-usage.json"
CLUSTER_NODES_FILE = ROOT / "config" / "imp-cluster-nodes.json"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def get_system_usage():

    cpu_usage = os.popen("grep 'cpu ' /proc/stat").read().strip()

    memory_usage = os.popen("free -m").read().strip()

    

    return {

        "CPU": cpu_usage,

        "Memory": memory_usage

    }



def balance_resources():

    nodes = []

    if os.path.exists(CLUSTER_NODES_FILE):

        with open(CLUSTER_NODES_FILE, "r") as f:

            nodes = json.load(f)



    usage = get_system_usage()

    

    remote_dir = os.environ.get("IMP_REMOTE_DIR", str(ROOT))

    for node in nodes:
        print(f"Checking resource balance for {node}...")
        if node in LOCAL_HOSTS:
            continue
        subprocess.run(
            f"ssh {node} 'python3 {remote_dir}/expansion/imp-resource-balancer.py'",
            shell=True,
        )


    with open(RESOURCE_LOG, "w") as f:

        json.dump(usage, f, indent=4)



if __name__ == "__main__":
    balance_resources()
