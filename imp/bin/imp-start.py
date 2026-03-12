import logging
import os
import sys
import time
from multiprocessing import Process, freeze_support
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
REPO_ROOT = CURRENT_FILE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from imp.runtime import IMP_ROOT as ROOT
from imp.runtime import LOG_DIR, PID_FILE, START_STATE_FILE, configure_file_logger, ensure_runtime_dirs, load_module, runtime_state, write_json


START_LOG = LOG_DIR / "imp-start-runtime.log"


def _run_module_function(module_name: str, path: Path, func_name: str) -> None:
    logger = configure_file_logger(module_name, LOG_DIR / f"imp-start-{module_name}.log")
    logger.info("Launching %s:%s from %s", module_name, func_name, path)
    try:
        module = load_module(module_name, path)
        getattr(module, func_name)()
        logger.info("%s:%s completed", module_name, func_name)
    except Exception:
        logger.exception("%s:%s failed", module_name, func_name)
        raise


def main():
    ensure_runtime_dirs()
    log = configure_file_logger("imp-start", START_LOG)
    log.info("Starting IMP supervisor")

    specs = [
        ("imp_execute", ROOT / "core" / "imp-execute.py", "main"),
        ("imp_learning_memory", ROOT / "core" / "imp-learning-memory.py", "store_learnings"),
        ("imp_strategy_generator", ROOT / "core" / "imp-strategy-generator.py", "generate_new_strategy"),
        ("imp_code_updater", ROOT / "self-improvement" / "imp-code-updater.py", "main"),
        ("imp_security_optimizer", ROOT / "security" / "imp-security-optimizer.py", "run_security_checks"),
        ("imp_cluster_manager", ROOT / "expansion" / "imp-cluster-manager.py", "distribute_workload"),
    ]
    processes = [Process(target=_run_module_function, args=spec, name=spec[0]) for spec in specs]

    try:
        write_json(
            START_STATE_FILE,
            runtime_state(
                "starting",
                modules=[name for name, _, _ in specs],
                started_at=time.time(),
                cwd=os.getcwd(),
            ),
        )
        started = []
        for p in processes:
            p.start()
            log.info("Started %s pid=%s", p.name, p.pid)
            started.append(p)

        write_json(PID_FILE, [{"name": p.name, "pid": p.pid} for p in started])
        write_json(
            START_STATE_FILE,
            runtime_state(
                "running",
                modules=[name for name, _, _ in specs],
                processes=[{"name": p.name, "pid": p.pid} for p in started],
                started_at=time.time(),
                cwd=os.getcwd(),
            ),
        )

        print("IMP AI is now running.")
        log.info("IMP AI is now running")

        exit_reported = {}
        poll_count = 0
        while True:
            any_alive = False
            for p in started:
                if p.is_alive():
                    any_alive = True
                elif p.exitcode is not None and not exit_reported.get(p.name):
                    log.warning("%s exited with code %s", p.name, p.exitcode)
                    print(f"[!] {p.name} exited with code {p.exitcode}")
                    exit_reported[p.name] = True
            if not any_alive:
                log.info("All IMP processes exited")
                break
            poll_count += 1
            time.sleep(5 if poll_count < 12 else 30)
    except KeyboardInterrupt:
        print("Shutting down IMP processes...")
        log.info("Shutdown requested by keyboard interrupt")
    finally:
        for p in processes:
            if p.is_alive():
                p.terminate()
        for p in processes:
            if p.pid is not None:
                p.join(timeout=5)
        write_json(
            START_STATE_FILE,
            runtime_state(
                "stopped",
                modules=[name for name, _, _ in specs],
                processes=[{"name": p.name, "pid": p.pid, "exitcode": p.exitcode} for p in processes],
                finished_at=time.time(),
                cwd=os.getcwd(),
            ),
        )
        log.info("IMP supervisor finished")


if __name__ == '__main__':
    freeze_support()
    main()
