"""Coordinate multiprocessing groups with per-group threading control."""

from __future__ import annotations

import os
import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from multiprocessing import Process
from pathlib import Path
from time import sleep, time
from typing import Any, Dict, Iterable, List, Sequence, Tuple

CORE_DIR = Path(__file__).resolve().parent
ROOT = CORE_DIR.parent
EXPANSION_DIR = ROOT / "expansion"

current_module = sys.modules.get(__name__)
if current_module is not None:
    sys.modules.setdefault("imp_processing_manager", current_module)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
load_module = utils.load_module
read_json = utils.read_json
write_json = utils.write_json

neural_manager = load_module("imp_neural_manager", CORE_DIR / "imp_neural_manager.py").manager
ProcessingManagerNN = load_module("imp_processing_nn", CORE_DIR / "imp-processing-nn.py").ProcessingManagerNN
ProcessingOptimizerNN = load_module(
    "imp_processing_optimizer_nn", CORE_DIR / "imp-processing-optimizer-nn.py"
).ProcessingOptimizerNN
ProcessingResilience = load_module(
    "imp_processing_resilience", CORE_DIR / "imp-processing-resilience.py"
).ProcessingResilience
resource_engine = load_module("imp_resource_engine", CORE_DIR / "imp-resource-engine.py")


def _load_distributed_queue():
    return load_module("imp_distributed_queue", EXPANSION_DIR / "imp-distributed-queue.py")


def _load_cluster_manager():
    return load_module("imp_cluster_manager", EXPANSION_DIR / "imp-cluster-manager.py")


def _load_load_scheduler():
    return load_module("imp_load_scheduler", EXPANSION_DIR / "imp-load-scheduler.py")


def _load_node_communicator():
    return load_module("imp_node_communicator", EXPANSION_DIR / "imp-node-communicator.py")


def _load_node_control():
    return load_module("imp_node_control", EXPANSION_DIR / "imp-node-control.py")


def _load_cloud_orchestrator():
    return load_module("imp_cloud_orchestrator", EXPANSION_DIR / "imp-cloud-orchestrator.py")


def _load_processing_security():
    return load_module("imp_processing_security", ROOT / "security" / "imp-processing-security.py")


PROCESSING_LOG = ROOT / "logs" / "imp-processing-log.json"
PROCESSING_LOG_LIMIT = 500

# Specs are (module_name, module_path, function_name)
Spec = Tuple[str, str, str]


def _resolve_callables(specs: Sequence[Spec]):
    callables = []
    for module_name, path_str, function_name in specs:
        module = load_module(module_name, Path(path_str))
        callables.append((getattr(module, function_name), (module_name, path_str, function_name)))
    return callables


def _append_processing_event(entry: Dict[str, Any]) -> None:
    """Persist a processing event while capping historical size."""

    record = dict(entry)
    record.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
    history = read_json(PROCESSING_LOG, [])
    history.append(record)
    if len(history) > PROCESSING_LOG_LIMIT:
        history = history[-PROCESSING_LOG_LIMIT:]
    write_json(PROCESSING_LOG, history)


def _sync_remote_nodes(meta: Dict[str, Any]) -> None:
    """Synchronize project files to cluster nodes when requested."""
    if not meta.get("sync_cluster", False):
        return
    try:
        cluster_manager = _load_cluster_manager()
        cluster_manager.distribute_workload()
    except Exception:
        # Remote sync failures are logged by remote utilities.
        return


def _dispatch_remote_tasks(
    remote_tasks: Sequence[str],
    meta: Dict[str, Any],
    backlog: int | None = None,
) -> None:
    """Queue remote commands and notify nodes to execute them."""
    if not remote_tasks:
        return

    try:
        distributed_queue = _load_distributed_queue()
    except Exception:
        return

    try:
        load_scheduler = _load_load_scheduler()
        nodes = load_scheduler.get_available_nodes()
    except Exception:
        nodes = []

    if not nodes:
        try:
            cluster_manager = _load_cluster_manager()
            nodes = cluster_manager.get_cluster_nodes()
        except Exception:
            nodes = []

    node_statuses = []
    try:
        node_control = _load_node_control()
        node_statuses = node_control.resolve_nodes(nodes)
        node_control.record_statuses(node_statuses)
        node_control.update_health(node_statuses)
        reachable = node_control.reachable_hosts(node_statuses)
        if reachable:
            nodes = reachable
    except Exception:
        pass

    orchestrator_plan: Dict[str, Any] | None = None
    capacities: Dict[str, int] | None = None
    stagger_delay: float = 0.0
    if meta.get("adaptive_orchestration", True):
        try:
            orchestrator = _load_cloud_orchestrator().CloudOrchestrator()
            orchestrator_plan = orchestrator.plan(
                nodes,
                node_statuses,
                meta,
                backlog=backlog,
            )
        except Exception:
            orchestrator_plan = None
        if orchestrator_plan:
            nodes = orchestrator_plan.get("nodes", nodes)
            new_interval = orchestrator_plan.get("interval")
            if isinstance(new_interval, (int, float)) and new_interval > 0:
                meta["remote_interval"] = float(new_interval)
            capacities = orchestrator_plan.get("capacities")
            stagger_value = orchestrator_plan.get("stagger")
            if isinstance(stagger_value, (int, float)):
                stagger_delay = float(stagger_value)
            elif isinstance(meta.get("remote_stagger"), (int, float)):
                stagger_delay = float(meta["remote_stagger"])

    try:
        processing_security = _load_processing_security()
        assessment = processing_security.assess_processing_nodes(
            nodes,
            statuses=node_statuses,
            meta={"group": meta.get("name")},
            orchestrator_plan=orchestrator_plan,
            backlog=backlog,
        )
        filtered = assessment.get("allowed_nodes")
        if isinstance(filtered, list):
            nodes = filtered
    except Exception:
        pass

    if not nodes:
        return

    remote_dir = meta.get("remote_dir") or os.environ.get("IMP_REMOTE_DIR", str(ROOT))
    formatted_tasks = [task.format(remote_dir=remote_dir) for task in remote_tasks]

    for command in formatted_tasks:
        try:
            distributed_queue.ensure_task(command)
        except AttributeError:
            distributed_queue.add_task(command)

    try:
        assignments = distributed_queue.assign_tasks(nodes, capacities=capacities)
    except TypeError:
        assignments = distributed_queue.assign_tasks(nodes)

    try:
        if 'node_control' not in locals():
            node_control = _load_node_control()
        node_control.record_assignments(
            assignments,
            tasks=formatted_tasks,
            remote_dir=remote_dir,
        )
    except Exception:
        pass

    if orchestrator_plan:
        telemetry = orchestrator_plan.get("telemetry")
        if telemetry:
            _append_processing_event(
                {
                    "event": "cloud_orchestration",
                    "group": meta.get("name"),
                    "data": telemetry,
                }
            )

    dispatcher = meta.get("remote_dispatcher")
    if dispatcher:
        dispatcher(assignments)
        return

    try:
        communicator = _load_node_communicator()
    except Exception:
        return

    assignment_items = list(assignments.items())
    total_items = len(assignment_items)
    for index, (node, commands) in enumerate(assignment_items):
        for command in commands:
            message = f"EXECUTE {command}"
            try:
                communicator.send_secure_message(node, message)
            except Exception:
                continue
        if stagger_delay > 0 and index < total_items - 1:
            sleep(min(5.0, stagger_delay))


def _group_worker(
    name: str,
    specs: Sequence[Spec],
    max_cycles: int | None,
    max_threads: int | None,
    meta: Dict[str, Any] | None,
) -> None:
    """Run a functionality group inside its own process."""
    controller = neural_manager.get_or_create("processing", ProcessingManagerNN)
    optimizer = neural_manager.get_or_create("processing_optimizer", ProcessingOptimizerNN)
    resilience = ProcessingResilience()
    remote_meta = meta or {}
    remote_tasks: Sequence[str] = tuple(remote_meta.get("remote_tasks", ()) or ())
    try:
        remote_interval = float(remote_meta.get("remote_interval", 180.0))
    except Exception:
        remote_interval = 180.0
    if remote_tasks:
        remote_meta.setdefault("name", name)
    last_remote_dispatch = 0.0
    cycle = 0
    if remote_tasks and remote_meta.get("sync_cluster", False):
        _sync_remote_nodes(remote_meta)
    while max_cycles is None or cycle < max_cycles:
        resource_record = resource_engine.manage_resources()
        resource_score = float(resource_record.get("score", 50.0))
        backlog = len(specs)
        base_threads = controller.recommend_threads(name, resource_score, backlog)
        plan = optimizer.plan_allocation(name, resource_score, backlog, base_threads)
        threads = int(plan.get("threads", base_threads))
        if max_threads is not None:
            threads = min(threads, max_threads)
        threads = max(1, threads)

        callables = _resolve_callables(specs)
        start = time()
        errors = 0
        failure_details: List[Tuple[Spec, str]] = []
        failed_specs: List[Spec] = []
        with ThreadPoolExecutor(max_workers=max(1, threads)) as executor:
            future_map = {
                executor.submit(func): spec for func, spec in callables
            }
            for future, spec in future_map.items():
                try:
                    future.result()
                except Exception as exc:  # pragma: no cover - logged via telemetry
                    errors += 1
                    failed_specs.append(spec)
                    failure_details.append((spec, repr(exc)))
        duration = time() - start
        if failed_specs and remote_meta.get("enable_resilience", True):
            resilience.record_failures(
                name,
                failure_details,
                duration=duration,
                backlog=backlog,
                resource_score=resource_score,
            )
            retry_stats = resilience.retry_failures(name, failed_specs)
            resolved_specs = retry_stats.get("resolved_specs", [])
            remaining_specs = retry_stats.get("remaining", [])
            if resolved_specs:
                resilience.record_recovery(name, resolved_specs)
            if remaining_specs:
                resilience.record_unresolved(name, remaining_specs)
            resolved_count = retry_stats.get("resolved", 0)
            if resolved_count:
                errors = max(0, errors - resolved_count)
        controller.record_cycle(name, duration, threads, resource_score, errors, backlog)
        optimizer.record_cycle(name, duration, threads, resource_score, errors, backlog)

        if remote_tasks:
            now = time()
            if now - last_remote_dispatch >= max(1e-3, remote_interval):
                dispatcher = remote_meta.get("remote_dispatcher")
                if dispatcher:
                    try:
                        dispatcher(tuple(remote_tasks))
                    except Exception:
                        pass
                else:
                    _dispatch_remote_tasks(remote_tasks, remote_meta, backlog)
                remote_interval = float(remote_meta.get("remote_interval", remote_interval))
                last_remote_dispatch = now
                _append_processing_event(
                    {
                        "event": "remote_dispatch",
                        "group": name,
                        "tasks": list(remote_tasks),
                        "interval": remote_interval,
                    }
                )

        _append_processing_event(
            {
                "event": "cycle",
                "group": name,
                "duration": float(round(duration, 6)),
                "threads": threads,
                "errors": errors,
                "resource_score": float(resource_score),
                "backlog": backlog,
            }
        )

        cycle += 1
        if max_cycles is not None and cycle >= max_cycles:
            break
        pause = plan.get("pause")
        if pause is None:
            pause = controller.recommend_pause(name)
        sleep(max(0.1, float(pause)))


class ProcessingManager:
    """High-level interface for registering and launching functionality groups."""

    def __init__(self, max_threads: int = 4, max_cycles: int | None = None) -> None:
        self.max_threads = max_threads
        self.max_cycles = max_cycles
        self.groups: Dict[str, List[Spec]] = {}
        self.processes: List[Process] = []
        self.group_meta: Dict[str, Dict[str, Any]] = {}

    def register_group(self, name: str, specs: Iterable[Spec], *, options: Dict[str, Any] | None = None) -> None:
        self.groups[name] = list(specs)
        self.group_meta[name] = dict(options or {})

    def register_groups(self, mapping: Dict[str, Iterable[Spec] | Dict[str, Any]]) -> None:
        for name, value in mapping.items():
            if isinstance(value, dict):
                specs = value.get("specs", [])
                options = value.get("options")
            else:
                specs = value
                options = None
            self.register_group(name, specs, options=options)

    def start(self) -> None:
        optimizer = neural_manager.get_or_create("processing_optimizer", ProcessingOptimizerNN)
        ordered = sorted(
            self.groups.items(),
            key=lambda item: optimizer.bootstrap_priority(item[0], len(item[1])),
            reverse=True,
        )
        for name, specs in ordered:
            meta = self.group_meta.get(name, {})
            process = Process(
                target=_group_worker,
                args=(name, specs, self.max_cycles, self.max_threads, meta),
            )
            process.daemon = True
            process.start()
            self.processes.append(process)

    def wait(self) -> None:
        for process in self.processes:
            process.join()
