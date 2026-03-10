"""Engine that uses CollaboratoryNN for collaborative network decisions."""

import importlib.util
from pathlib import Path
from typing import List

CORE_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("imp_utils", CORE_DIR / "imp_utils.py")
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)
load_module = utils.load_module

CollaboratoryNN = load_module("collab_nn", CORE_DIR / "imp-collaboratory-nn.py").CollaboratoryNN
neural_manager = load_module("imp_neural_manager", CORE_DIR / "imp_neural_manager.py").manager

MODEL_PATH = CORE_DIR.parents[1] / "logs" / "collaboratory_nn.json"


def load_model(input_len: int) -> CollaboratoryNN:
    def factory() -> CollaboratoryNN:
        if MODEL_PATH.exists():
            return CollaboratoryNN.load(MODEL_PATH)
        return CollaboratoryNN(input_len, 4, 1)
    return neural_manager.get_or_create('collaboratory', factory)


def run_collaboration(inputs: List[float]) -> float:
    """Run the collaboratory network on provided inputs."""
    net = load_model(len(inputs))
    out = net.forward(inputs)[0]
    net.save(MODEL_PATH)
    return out


if __name__ == "__main__":
    print(run_collaboration([0.0, 0.0]))
