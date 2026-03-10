from pathlib import Path
import importlib.util
import subprocess
import logging
import sys


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORE_DIR = Path(__file__).resolve().parent
utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
load_module = utils.load_module

neural_manager = load_module("imp_neural_manager", CORE_DIR / "imp_neural_manager.py").manager
DefenseNN = load_module("imp-defense-nn", CORE_DIR / "imp-defense-nn.py").DefenseNN

ROOT = CORE_DIR.parent
MODEL_PATH = ROOT / "models" / "defense_nn.json"
AUDIT_LOG = ROOT / "logs" / "imp-network-audit.json"
DEFENSE_SCRIPT = ROOT / "security" / "imp-automated-defense.py"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def load_model() -> DefenseNN:
    def factory() -> DefenseNN:
        if MODEL_PATH.exists():
            return DefenseNN.load(MODEL_PATH)
        return DefenseNN(1, 2, 1)

    return neural_manager.get_or_create("defense", factory)


def suspicious_count() -> int:
    data = read_json(AUDIT_LOG, [])
    return len(data)


def run_defense_cycle() -> None:
    model = load_model()
    count = suspicious_count()
    output = model.forward([count / 10.0])[0]
    log.info("Defense model output: %.3f", output)
    if output > 0.5:
        subprocess.run([sys.executable, str(DEFENSE_SCRIPT)], check=False)
    else:
        log.info("No defense action required.")


if __name__ == "__main__":
    run_defense_cycle()
