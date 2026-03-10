from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / 'logs' / 'imp-distributed-queue.json'


def _load_queue() -> list[dict]:
    if QUEUE_FILE.exists():
        try:
            with open(QUEUE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def _save_queue(queue: list[dict]) -> None:
    with open(QUEUE_FILE, 'w') as f:
        json.dump(queue, f, indent=4)


def add_task(command: str) -> None:
    """Add a new task to the distributed queue."""
    queue = _load_queue()
    queue.append({'command': command, 'node': None, 'status': 'pending'})
    _save_queue(queue)


def ensure_task(command: str) -> None:
    """Ensure a command exists in the queue without creating duplicates."""
    queue = _load_queue()
    for task in queue:
        if task['command'] == command and task['status'] in {'pending', 'assigned'}:
            return
    queue.append({'command': command, 'node': None, 'status': 'pending'})
    _save_queue(queue)


def assign_tasks(
    nodes: Sequence[str],
    *,
    capacities: Mapping[str, int] | None = None,
) -> Dict[str, list[str]]:
    """Assign pending tasks across *nodes* respecting optional capacity weights."""

    nodes = [str(node) for node in nodes]
    queue = _load_queue()
    pending = [t for t in queue if t['status'] == 'pending']
    if not pending or not nodes:
        return {}

    node_cycle = _build_cycle(nodes, capacities)
    assignments: Dict[str, list[str]] = {}
    for i, task in enumerate(pending):
        node = node_cycle[i % len(node_cycle)]
        task['node'] = node
        task['status'] = 'assigned'
        assignments.setdefault(node, []).append(task['command'])
    _save_queue(queue)
    return assignments


def _build_cycle(nodes: Sequence[str], capacities: Mapping[str, int] | None) -> list[str]:
    if not capacities:
        return list(nodes)

    weights = {}
    for node in nodes:
        raw = capacities.get(node)
        if raw is None:
            raw = capacities.get(str(node))
        weight = max(1, int(raw or 0))
        weights[str(node)] = weight

    total = sum(weights.values())
    if total <= 0:
        return list(nodes)

    # Build a weighted cycle while keeping the list manageable.
    cycle: list[str] = []
    limit = max(len(nodes), min(total, 64))
    sorted_nodes = sorted(nodes, key=lambda n: weights.get(n, 1), reverse=True)
    for node in sorted_nodes:
        repeats = max(1, min(weights[node], limit))
        cycle.extend([node] * repeats)
        if len(cycle) >= limit:
            break

    if len(cycle) < len(nodes):
        for node in nodes:
            if len(cycle) >= limit:
                break
            if node not in cycle:
                cycle.append(node)

    if not cycle:
        cycle = list(nodes)

    return cycle


def get_assigned(node: str) -> list[str]:
    """Retrieve tasks assigned to a specific node."""
    queue = _load_queue()
    tasks = [t['command'] for t in queue if t['node'] == node and t['status'] == 'assigned']
    return tasks


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='IMP Distributed Queue')
    parser.add_argument('--add', help='Add a task command')
    parser.add_argument('--assign', action='store_true', help='Assign tasks to nodes from config')
    parser.add_argument('--node', help='Get tasks assigned to a node')
    args = parser.parse_args()

    if args.add:
        add_task(args.add)
        print('Task added')
    elif args.assign:
        config_path = ROOT / 'config' / 'imp-cluster-nodes.json'
        nodes = []
        if config_path.exists():
            with open(config_path, 'r') as f:
                nodes = json.load(f)
        assignments = assign_tasks(nodes)
        print(json.dumps(assignments, indent=4))
    elif args.node:
        print(get_assigned(args.node))
