from multiprocessing import Process, freeze_support
from pathlib import Path
import importlib.util
import logging
import sys
import time

# Determine repository root so modules load correctly on all platforms
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(name: str, path: Path):
    """Dynamically load a module from the given file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LOG_DIR = ROOT / "logs"
PID_FILE = LOG_DIR / "imp-pids.json"
START_LOG = LOG_DIR / "imp-start-runtime.log"


def _configure_logger(name: str, path: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def _run_module_function(module_name: str, path: Path, func_name: str) -> None:
    logger = _configure_logger(module_name, LOG_DIR / f"imp-start-{module_name}.log")
    logger.info("Launching %s:%s from %s", module_name, func_name, path)
    try:
        module = _load(module_name, path)
        getattr(module, func_name)()
        logger.info("%s:%s completed", module_name, func_name)
    except Exception:
        logger.exception("%s:%s failed", module_name, func_name)
        raise


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = _configure_logger("imp-start", START_LOG)
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
        started = []
        for p in processes:
            p.start()
            log.info("Started %s pid=%s", p.name, p.pid)
            started.append(p)

        with open(PID_FILE, "w", encoding="utf-8") as f:
            import json
            json.dump(
                [{"name": p.name, "pid": p.pid} for p in started],
                f,
                indent=2,
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
        log.info("IMP supervisor finished")


if __name__ == '__main__':
    freeze_support()
    main()
