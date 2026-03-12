from pathlib import Path
import importlib.util
import sys

CORE_DIR = Path(__file__).resolve().parent

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

manager_module = _load('imp_neural_manager', CORE_DIR / 'imp_neural_manager.py')
neural_manager = manager_module.manager
ResourceNN = _load('imp_resource_nn', CORE_DIR / 'imp-resource-nn.py').ResourceNN
DefenseNN = _load('imp_defense_nn', CORE_DIR / 'imp-defense-nn.py').DefenseNN
NetworkTaskNN = _load('imp_network_task_nn', CORE_DIR / 'imp-network-task-nn.py').NetworkTaskNN
BBINN = _load('imp_bbi_nn', CORE_DIR / 'imp-bbi-nn.py').BBINN
CollaboratoryNN = _load('imp_collaboratory_nn', CORE_DIR / 'imp-collaboratory-nn.py').CollaboratoryNN
AdversarialNN = _load('imp_adversarial_nn', CORE_DIR / 'imp-adversarial-nn.py').AdversarialNN
ProcessingManager = _load('imp_processing_manager', CORE_DIR / 'imp-processing-manager.py').ProcessingManager
ProcessingManagerNN = _load('imp_processing_nn', CORE_DIR / 'imp-processing-nn.py').ProcessingManagerNN

# Load submodules dynamically so file names with dashes work as imports
ROOT = CORE_DIR.parents[0]
sys.path.insert(0, str(ROOT))

codelock = _load("imp_code_lock", ROOT / "security" / "imp-code-lock.py")
# Processing manager pulls functional modules on demand.

def _group_spec(module: str, path: Path, function: str):
    return (module, str(path), function)
# 2025-06-08: Execution harness should remain additive and retain prior
# processes. Consider a reflective recursive enumeration blockchain for
# self-healing and memory preservation.


def init_networks() -> None:
    """Register core neural networks so IMP controls them centrally."""
    neural_manager.register("resource", ResourceNN())
    neural_manager.register("defense", DefenseNN(1, 2, 1))
    neural_manager.register("network_task", NetworkTaskNN(1, 2, 1))
    neural_manager.register("bbi", BBINN(2, 2, 1))
    neural_manager.register("collaboratory", CollaboratoryNN(2, 4, 1))
    neural_manager.register("adversarial", AdversarialNN(2, 2))
    neural_manager.register("processing", ProcessingManagerNN())


def _build_groups():
    return {
        "autonomy": [
            _group_spec(
                "imp_autonomy_controller",
                ROOT / "core" / "imp-autonomy-controller.py",
                "govern",
            ),
        ],
        "knowledge": [
            _group_spec("imp_learning_memory", ROOT / "core" / "imp-learning-memory.py", "store_learnings"),
            _group_spec("imp_strategy_generator", ROOT / "core" / "imp-strategy-generator.py", "generate_new_strategy"),
        ],
        "self_improvement": {
            "specs": [
                _group_spec("imp_code_updater", ROOT / "self-improvement" / "imp-code-updater.py", "main"),
            ],
            "options": {
                "remote_tasks": [
                    "python3 {remote_dir}/self-improvement/imp-code-updater.py --mode auto",
                ],
                "remote_interval": 900.0,
            },
        },
        "security": [
            _group_spec("imp_security_optimizer", ROOT / "security" / "imp-security-optimizer.py", "run_security_checks"),
            _group_spec("imp_cyber_researcher", ROOT / "security" / "imp-cyber-researcher.py", "run_forever"),
        ],
        "expansion": {
            "specs": [
                _group_spec("imp_cluster_manager", ROOT / "expansion" / "imp-cluster-manager.py", "distribute_workload"),
                _group_spec("imp_load_scheduler", ROOT / "expansion" / "imp-load-scheduler.py", "schedule_tasks"),
            ],
            "options": {
                "remote_tasks": [
                    "python3 {remote_dir}/expansion/imp-load-scheduler.py",
                    "python3 {remote_dir}/expansion/imp-cluster-manager.py",
                ],
                "remote_interval": 300.0,
                "sync_cluster": True,
            },
        },
    }

def build_manager(max_threads=None, max_cycles=None):
    manager = ProcessingManager(max_threads=max_threads, max_cycles=max_cycles)
    manager.register_groups(_build_groups())
    return manager


def main():
    print("IMP AI is initializing...")
    codelock.lock_repo()
    init_networks()

    manager = build_manager()
    manager.start()

    print("IMP is now running autonomously.")

    manager.wait()

if __name__ == "__main__":
    main()
