"""Regression test for the load scheduler module.

The scheduler previously lacked automated coverage which meant queue
assignments or subprocess handling regressions could slip through.  This
exercise uses a temporary queue file and a mocked subprocess runner so we can
verify task assignment logic without needing real network nodes.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "expansion" / "imp-load-scheduler.py"


def _load_scheduler():
    spec = importlib.util.spec_from_file_location("imp_load_scheduler", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_scheduler_assigns_tasks():
    print("Running Load Scheduler Test...")
    scheduler = _load_scheduler()

    temp_dir = Path(tempfile.mkdtemp())
    queue_file = temp_dir / "queue.json"
    tasks_file = temp_dir / "tasks.json"
    nodes_file = temp_dir / "nodes.json"
    nodes = ["node-alpha", "node-beta"]
    nodes_file.write_text(json.dumps(nodes))

    original_nodes_file = scheduler.CLUSTER_NODES_FILE
    original_tasks_file = scheduler.TASKS_FILE
    original_queue_file = scheduler.dq.QUEUE_FILE
    previous_remote_dir = os.environ.get("IMP_REMOTE_DIR")
    remote_dir = str(temp_dir / "repo")

    os.environ["IMP_REMOTE_DIR"] = remote_dir
    scheduler.CLUSTER_NODES_FILE = nodes_file
    scheduler.TASKS_FILE = tasks_file
    scheduler.dq.QUEUE_FILE = queue_file

    ssh_calls = []

    def fake_run(cmd, shell, capture_output=False, text=False):
        if "ping" in cmd:
            return SimpleNamespace(returncode=0)
        if "ssh" in cmd:
            ssh_calls.append(cmd)
            return SimpleNamespace(returncode=0)
        return SimpleNamespace(returncode=0)

    assigned_data = None
    queue_snapshot = None
    try:
        with patch.object(scheduler.subprocess, "run", side_effect=fake_run):
            scheduler.schedule_tasks()
        assigned_data = json.loads(tasks_file.read_text())
        queue_snapshot = json.loads(queue_file.read_text())
    finally:
        scheduler.CLUSTER_NODES_FILE = original_nodes_file
        scheduler.TASKS_FILE = original_tasks_file
        scheduler.dq.QUEUE_FILE = original_queue_file
        if previous_remote_dir is None:
            os.environ.pop("IMP_REMOTE_DIR", None)
        else:
            os.environ["IMP_REMOTE_DIR"] = previous_remote_dir
        shutil.rmtree(temp_dir)

    assert ssh_calls, "scheduler should attempt to dispatch commands over SSH"
    assert assigned_data is not None
    assert queue_snapshot is not None
    assert set(assigned_data.keys()) == set(nodes)

    expected_commands = {
        f"python3 {remote_dir}/self-improvement/imp-code-updater.py",
        f"python3 {remote_dir}/security/imp-security-optimizer.py",
        f"python3 {remote_dir}/expansion/imp-resource-balancer.py",
    }

    dispatched = {cmd for cmds in assigned_data.values() for cmd in cmds}
    assert expected_commands == dispatched

    statuses = {entry["status"] for entry in queue_snapshot}
    assert statuses == {"assigned"}
    print("Load Scheduler Test Passed")


if __name__ == "__main__":
    test_load_scheduler_assigns_tasks()
