from pathlib import Path
import importlib.util
import random
import json
import os

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-neural-network.py"
SKIP_LEDGER = os.environ.get("IMP_DISABLE_LEDGER_RESTORE") == "1"

spec = importlib.util.spec_from_file_location("imp_neural_network", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_forward():
    print("Testing Base Neural Network...")
    net = module.SimpleNeuralNetwork(3, 2, 1, activation="sigmoid")
    out = net.forward([0.5, -0.2, 0.1])
    assert len(out) == 1
    print("Neural Network Test Passed!")

def test_save_load():
    print("Testing Neural Network Save/Load...")
    net = module.SimpleNeuralNetwork(2, 2, 1, activation="sigmoid")
    tmp = ROOT / "nn_tmp.json"
    net.save(tmp)
    loaded = module.SimpleNeuralNetwork.load(tmp)
    out1 = net.forward([0.1, 0.2])
    out2 = loaded.forward([0.1, 0.2])
    assert out1 == out2
    assert loaded.activation == "sigmoid"
    assert loaded.b1 == net.b1
    tmp.unlink()
    print("Save/Load Test Passed!")

def test_training():
    print("Testing Neural Network Training...")
    random.seed(0)
    net = module.SimpleNeuralNetwork(2, 2, 1)
    data = [([0, 0], [0]), ([0, 1], [1]), ([1, 0], [1]), ([1, 1], [1])]
    before = net.forward([1, 0])[0]
    for _ in range(50):
        net.train(data, epochs=1)
    after = net.forward([1, 0])[0]
    assert abs(after - 1) < abs(before - 1)
    print("Training Test Passed!")


def test_momentum_update():
    print("Testing Momentum Updates...")
    net = module.SimpleNeuralNetwork(2, 2, 1, momentum=0.5)
    before = [row[:] for row in net.w1]
    net.update_weights([0.1, 0.2], [0.3], learning_rate=0.1)
    changed = any(net.w1[i][j] != before[i][j] for i in range(2) for j in range(2))
    assert changed
    print("Momentum Update Test Passed!")


def test_weight_decay():
    print("Testing Weight Decay...")
    net = module.SimpleNeuralNetwork(2, 2, 1, weight_decay=0.1)
    inputs = [0.1, 0.2]
    target = net.forward(inputs)
    before = [row[:] for row in net.w1]
    net.update_weights(inputs, target, learning_rate=0.1)
    after = net.w1
    for i in range(2):
        for j in range(2):
            assert abs(after[i][j]) < abs(before[i][j])
    print("Weight Decay Test Passed!")


def test_dropout():
    print("Testing Dropout...")
    random.seed(0)
    net = module.SimpleNeuralNetwork(2, 10, 1, dropout=0.5)
    _, hidden, _ = net.forward([0.1, 0.2], return_hidden=True, training=True)
    dropped = sum(1 for h in hidden if h == 0.0)
    assert dropped > 0
    print("Dropout Test Passed!")


def test_adam_optimizer():
    print("Testing Adam Optimizer...")
    net = module.SimpleNeuralNetwork(2, 2, 1, optimizer="adam")
    before = [row[:] for row in net.w1]
    net.update_weights([0.1, 0.2], [0.3], learning_rate=0.01)
    changed = any(net.w1[i][j] != before[i][j] for i in range(2) for j in range(2))
    assert changed
    print("Adam Optimizer Test Passed!")


def test_learning_rate_decay():
    print("Testing Learning Rate Decay...")
    net = module.SimpleNeuralNetwork(2, 2, 1)
    captured = []
    original = net.update_weights

    def capture(inputs, target, lr):
        captured.append(lr)
        return original(inputs, target, lr)

    net.update_weights = capture
    data = [([0, 0], [0])]
    net.train(data, epochs=3, learning_rate=0.1, lr_decay=0.5)
    assert captured == [0.1, 0.05, 0.025]
    print("Learning Rate Decay Test Passed!")


def test_mutation_lr_boost():
    print("Testing Mutation-Based Learning Rate Boost...")
    random.seed(0)
    net = module.SimpleNeuralNetwork(2, 2, 1)
    captured = []
    orig_update = net.update_weights

    def capture(inputs, target, lr):
        captured.append(lr)
        return orig_update(inputs, target, lr)

    net.update_weights = capture
    log = ROOT / "logs" / "imp-learning-memory.json"
    original_log = json.loads(log.read_text())
    data = [([0, 0], [0])]
    net.train(data, epochs=3, learning_rate=0.1, lr_decay=1.0, mutation_factor=1.0)
    updated = json.loads(log.read_text())
    assert len(updated) == len(original_log) + 3
    assert captured[1] >= captured[0]
    assert captured[2] >= captured[1]
    log.write_text(json.dumps(original_log))
    print("Mutation LR Boost Test Passed!")


def test_self_analysis_logging():
    print("Testing Self-Analysis Logging...")
    log = ROOT / "logs" / "imp-learning-memory.json"
    original = json.loads(log.read_text())
    net = module.SimpleNeuralNetwork(2, 2, 1)
    data = [([0, 0], [0])]
    net.train(data, epochs=4, mutation_factor=1.0, history_window=10)
    updated = json.loads(log.read_text())
    assert len(updated) == len(original) + 4
    entries = updated[-4:]
    last = entries[-1]
    avg_prev = sum(e["mutation"] for e in entries[:-1]) / (len(entries) - 1)
    assert "avg_mutation" in last
    assert abs(last["avg_mutation"] - avg_prev) < 1e-6
    assert abs(last["trend"] - (last["mutation"] - avg_prev)) < 1e-6
    log.write_text(json.dumps(original))
    print("Self-Analysis Logging Test Passed!")


def test_dynamic_restore_from_ledger():
    if SKIP_LEDGER:
        print("Skipping dynamic ledger restore in fast mode.")
        return
    print("Testing Dynamic Restore from Ledger...")
    net = module.SimpleNeuralNetwork(2, 2, 1)
    restored = net.dynamic_restore_from_ledger(threshold=0)
    assert isinstance(restored, list)
    print("Dynamic Restore Test Passed!")


def test_auto_restore_from_ledger():
    if SKIP_LEDGER:
        print("Skipping auto ledger restore in fast mode.")
        return
    print("Testing Auto Restore from Ledger...")
    net = module.SimpleNeuralNetwork(2, 2, 1)
    restored = net.auto_restore_from_ledger(threshold=0)
    assert isinstance(restored, list)
    print("Auto Restore Test Passed!")


def test_heal_from_ledger():
    if SKIP_LEDGER:
        print("Skipping heal from ledger in fast mode.")
        return
    print("Testing Heal from Ledger...")
    net = module.SimpleNeuralNetwork(2, 2, 1)
    assert hasattr(net, 'heal_from_ledger')
    net.heal_from_ledger()
    print("Heal from Ledger Test Passed!")


def test_restore_repository_from_ledger():
    if SKIP_LEDGER:
        print("Skipping repository restore in fast mode.")
        return
    print("Testing Repository Restore from Ledger...")
    net = module.SimpleNeuralNetwork(2, 2, 1)
    assert hasattr(net, 'restore_repository_from_ledger')
    restored = net.restore_repository_from_ledger()
    assert isinstance(restored, list)
    print("Repository Restore Test Passed!")

if __name__ == "__main__":
    test_forward()
    test_save_load()
    test_training()
    test_momentum_update()
    test_weight_decay()
    test_dropout()
    test_adam_optimizer()
    test_learning_rate_decay()
    test_mutation_lr_boost()
    test_self_analysis_logging()
    test_dynamic_restore_from_ledger()
    test_auto_restore_from_ledger()
    test_heal_from_ledger()
    test_restore_repository_from_ledger()
