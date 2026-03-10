import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_HEALTH_LOG = ROOT / "logs" / "imp-node-health.json"

def _is_online(status):
    if isinstance(status, str):
        return status.lower() == "online"
    if isinstance(status, dict):
        return str(status.get("state", "")).lower() == "online"
    return False

def test_node_health():
    print("Checking AI Cluster Nodes...")
    
    with open(NODE_HEALTH_LOG, "r") as f:
        nodes = json.load(f)
    
    assert all(_is_online(status) for status in nodes.values()), "Some AI nodes are offline!"
    
    print("AI Cluster Test Passed!")

test_node_health()
