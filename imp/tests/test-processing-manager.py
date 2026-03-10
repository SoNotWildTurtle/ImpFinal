from pathlib import Path
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[1]
NN_PATH = ROOT / "core" / "imp-processing-nn.py"
MANAGER_PATH = ROOT / "core" / "imp-processing-manager.py"
OPTIMIZER_PATH = ROOT / "core" / "imp-processing-optimizer-nn.py"
LOG_PATH = ROOT / "logs" / "imp-processing-log.json"
OPTIMIZER_LOG_PATH = ROOT / "logs" / "imp-processing-optimizer.json"
RESILIENCE_LOG_PATH = ROOT / "logs" / "imp-processing-resilience.json"

spec_nn = importlib.util.spec_from_file_location("imp_processing_nn", NN_PATH)
nn_module = importlib.util.module_from_spec(spec_nn)
spec_nn.loader.exec_module(nn_module)

spec_manager = importlib.util.spec_from_file_location("imp_processing_manager", MANAGER_PATH)
manager_module = importlib.util.module_from_spec(spec_manager)
spec_manager.loader.exec_module(manager_module)

spec_optimizer = importlib.util.spec_from_file_location("imp_processing_optimizer_nn", OPTIMIZER_PATH)
optimizer_module = importlib.util.module_from_spec(spec_optimizer)
spec_optimizer.loader.exec_module(optimizer_module)


def test_processing_nn_history_updates(tmp_path):
    nn = nn_module.ProcessingManagerNN(max_threads=4)
    base_threads = nn.recommend_threads("analysis", resource_score=80.0, backlog=0)
    assert base_threads >= 1

    scaled_threads = nn.recommend_threads("analysis", resource_score=20.0, backlog=2)
    assert scaled_threads >= base_threads

    nn.record_cycle("analysis", duration=1.2, threads=scaled_threads, resource_score=25.0, errors=0, backlog=2)
    history = nn.history("analysis")
    assert history and history[-1]["threads"] == scaled_threads


def test_processing_optimizer_plan_and_history(tmp_path):
    OPTIMIZER_LOG_PATH.write_text("[]")
    optimizer = optimizer_module.ProcessingOptimizerNN(max_threads=6)

    plan = optimizer.plan_allocation("analysis", resource_score=35.0, backlog=4, base_threads=2)
    assert plan["threads"] >= 2

    optimizer.record_cycle(
        "analysis",
        duration=2.0,
        threads=plan["threads"],
        resource_score=35.0,
        errors=1,
        backlog=4,
    )

    history = optimizer.history("analysis")
    assert any(entry["event"] == "plan" for entry in history)
    assert any(entry["event"] == "cycle" for entry in history)

    log = json.loads(OPTIMIZER_LOG_PATH.read_text())
    assert log and log[-1]["event"] == "cycle"


def test_group_worker_executes_spec(tmp_path):
    result_path = tmp_path / "result.txt"
    task_path = tmp_path / "processing_task.py"
    task_path.write_text(
        "from pathlib import Path\n"
        f"RESULT = Path(r'{result_path}')\n"
        "def run_task():\n"
        "    RESULT.write_text('complete')\n"
    )

    LOG_PATH.write_text("[]")
    OPTIMIZER_LOG_PATH.write_text("[]")
    RESILIENCE_LOG_PATH.write_text("[]")
    before = len(json.loads(LOG_PATH.read_text()))
    before_optimizer = len(json.loads(OPTIMIZER_LOG_PATH.read_text()))
    manager_module._group_worker(
        "test_group",
        [("processing_task_module", str(task_path), "run_task")],
        max_cycles=1,
        max_threads=2,
        meta={},
    )
    after = len(json.loads(LOG_PATH.read_text()))
    after_optimizer = len(json.loads(OPTIMIZER_LOG_PATH.read_text()))

    assert result_path.read_text() == "complete"
    assert after == before + 1
    assert after_optimizer >= before_optimizer + 1


def test_group_worker_remote_dispatch(tmp_path):
    result_path = tmp_path / "remote.txt"
    task_path = tmp_path / "remote_task.py"
    task_path.write_text(
        "from pathlib import Path\n"
        f"RESULT = Path(r'{result_path}')\n"
        "def run_remote():\n"
        "    RESULT.write_text('ran')\n"
    )

    calls = []

    def fake_dispatch(tasks):
        calls.append(tuple(tasks))

    manager_module._group_worker(
        "remote_group",
        [("remote_task", str(task_path), "run_remote")],
        max_cycles=1,
        max_threads=1,
        meta={
            "remote_tasks": ["python3 {remote_dir}/bin/fake-task.py"],
            "remote_dispatcher": fake_dispatch,
            "remote_interval": 0,
        },
    )

    assert result_path.read_text() == "ran"
    assert calls and calls[0][0] == "python3 {remote_dir}/bin/fake-task.py"


def test_group_worker_resilience_retry(tmp_path):
    state_path = tmp_path / "state.txt"
    task_path = tmp_path / "flaky_task.py"
    task_path.write_text(
        "from pathlib import Path\n"
        f"STATE = Path(r'{state_path}')\n"
        "def run_once():\n"
        "    count = 0\n"
        "    if STATE.exists():\n"
        "        count = int(STATE.read_text())\n"
        "    if count == 0:\n"
        "        STATE.write_text('1')\n"
        "        raise RuntimeError('planned failure')\n"
        "    STATE.write_text('2')\n"
    )

    LOG_PATH.write_text("[]")
    OPTIMIZER_LOG_PATH.write_text("[]")
    RESILIENCE_LOG_PATH.write_text("[]")

    manager_module._group_worker(
        "resilience_group",
        [("flaky_task", str(task_path), "run_once")],
        max_cycles=1,
        max_threads=1,
        meta={},
    )

    assert state_path.read_text() == "2"
    resilience_log = json.loads(RESILIENCE_LOG_PATH.read_text())
    events = {entry["event"] for entry in resilience_log}
    assert {"failure", "retry", "recovered"}.issubset(events)

    cycle_log = json.loads(LOG_PATH.read_text())
    assert cycle_log[-1]["errors"] == 0
