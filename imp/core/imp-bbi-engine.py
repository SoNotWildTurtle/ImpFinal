import importlib.util
from pathlib import Path


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CORE_DIR = Path(__file__).resolve().parent
utils = _load("imp_utils", CORE_DIR / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json
load_module = utils.load_module

neural_manager = load_module("imp_neural_manager", CORE_DIR / "imp_neural_manager.py").manager
BBINN = load_module("imp_bbi_nn", CORE_DIR / "imp-bbi-nn.py").BBINN

LOG = CORE_DIR.parent / "logs" / "imp-bbi-log.json"
MODEL = CORE_DIR.parent / "logs" / "imp-bbi-model.json"


class BBIEngine:
    """Manages BBI interactions and evolves its neural network."""

    def __init__(self):
        self.network = load_model()

    def record_interaction(self, user_signal: str, imp_signal: str, theme: str = ''):
        data = read_json(LOG, [])
        data.append({"user": user_signal, "imp": imp_signal, "theme": theme})
        write_json(LOG, data)
        before = self.network.hidden_size
        self.network.evolve()
        self.network.save(MODEL)
        return before, self.network.hidden_size


def load_model() -> BBINN:
    def factory() -> BBINN:
        if MODEL.exists():
            return BBINN.load(MODEL)
        return BBINN(2, 2, 1)
    return neural_manager.get_or_create('bbi', factory)
