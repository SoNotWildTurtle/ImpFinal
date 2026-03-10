import random
import json
import math
import importlib.util
from pathlib import Path
from typing import List, Iterable, Tuple

spec = importlib.util.spec_from_file_location("imp_utils", Path(__file__).resolve().parent / "imp_utils.py")
imp_utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp_utils)
read_json = imp_utils.read_json
write_json = imp_utils.write_json

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_LOG = ROOT / "logs" / "imp-learning-memory.json"

class SimpleNeuralNetwork:
    """A minimal feedforward neural network for future experimentation."""

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        output_size: int,
        activation: str = "relu",
        momentum: float = 0.0,
        weight_decay: float = 0.0,
        dropout: float = 0.0,
        optimizer: str = "sgd",
        beta1: float = 0.9,
        beta2: float = 0.999,
        epsilon: float = 1e-8,
    ):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        self.activation = activation
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.dropout = dropout
        self.optimizer = optimizer
        self.beta1 = beta1
        self.beta2 = beta2
        self.epsilon = epsilon
        self.t = 0
        self.last_lr = None
        self.w1 = [
            [random.uniform(-1, 1) for _ in range(hidden_size)]
            for _ in range(input_size)
        ]
        self.w2 = [
            [random.uniform(-1, 1) for _ in range(output_size)]
            for _ in range(hidden_size)
        ]
        self.b1 = [random.uniform(-1, 1) for _ in range(hidden_size)]
        self.b2 = [random.uniform(-1, 1) for _ in range(output_size)]
        self.v_w1 = [
            [0.0 for _ in range(hidden_size)]
            for _ in range(input_size)
        ]
        self.v_w2 = [
            [0.0 for _ in range(output_size)]
            for _ in range(hidden_size)
        ]
        self.v_b1 = [0.0 for _ in range(hidden_size)]
        self.v_b2 = [0.0 for _ in range(output_size)]
        if self.optimizer == "adam":
            self.m_w1 = [
                [0.0 for _ in range(hidden_size)]
                for _ in range(input_size)
            ]
            self.m_w2 = [
                [0.0 for _ in range(output_size)]
                for _ in range(hidden_size)
            ]
            self.m_b1 = [0.0 for _ in range(hidden_size)]
            self.m_b2 = [0.0 for _ in range(output_size)]
            self.s_w1 = [
                [0.0 for _ in range(hidden_size)]
                for _ in range(input_size)
            ]
            self.s_w2 = [
                [0.0 for _ in range(output_size)]
                for _ in range(hidden_size)
            ]
            self.s_b1 = [0.0 for _ in range(hidden_size)]
            self.s_b2 = [0.0 for _ in range(output_size)]

    def add_hidden_neuron(self):
        """Expand the hidden layer with a new neuron and random weights."""
        self.hidden_size += 1
        for i in range(self.input_size):
            self.w1[i].append(random.uniform(-1, 1))
            self.v_w1[i].append(0.0)
            if self.optimizer == "adam":
                self.m_w1[i].append(0.0)
                self.s_w1[i].append(0.0)
        self.w2.append([random.uniform(-1, 1) for _ in range(self.output_size)])
        self.v_w2.append([0.0 for _ in range(self.output_size)])
        if self.optimizer == "adam":
            self.m_w2.append([0.0 for _ in range(self.output_size)])
            self.s_w2.append([0.0 for _ in range(self.output_size)])
        self.b1.append(random.uniform(-1, 1))
        self.v_b1.append(0.0)
        if self.optimizer == "adam":
            self.m_b1.append(0.0)
            self.s_b1.append(0.0)

    def update_weights(self, inputs: List[float], target: List[float], learning_rate: float = 0.1) -> None:
        """Backpropagate error and adjust both weight matrices with momentum and dropout."""
        outputs, hidden, mask = self.forward(inputs, return_hidden=True, training=True)
        if len(target) != self.output_size:
            raise ValueError("Target vector size must match output size")
        errors = [target[i] - outputs[i] for i in range(self.output_size)]
        if self.optimizer == "adam":
            self.t += 1
        for k in range(self.output_size):
            g = errors[k]
            if self.optimizer == "adam":
                self.m_b2[k] = self.beta1 * self.m_b2[k] + (1 - self.beta1) * g
                self.s_b2[k] = self.beta2 * self.s_b2[k] + (1 - self.beta2) * (g ** 2)
                m_hat = self.m_b2[k] / (1 - self.beta1 ** self.t)
                s_hat = self.s_b2[k] / (1 - self.beta2 ** self.t)
                self.b2[k] += learning_rate * m_hat / (math.sqrt(s_hat) + self.epsilon)
            else:
                grad = learning_rate * g
                self.v_b2[k] = self.momentum * self.v_b2[k] + grad
                self.b2[k] += self.v_b2[k]
        for j in range(self.hidden_size):
            for k in range(self.output_size):
                g = errors[k] * hidden[j] - self.weight_decay * self.w2[j][k]
                if self.optimizer == "adam":
                    self.m_w2[j][k] = self.beta1 * self.m_w2[j][k] + (1 - self.beta1) * g
                    self.s_w2[j][k] = self.beta2 * self.s_w2[j][k] + (1 - self.beta2) * (g ** 2)
                    m_hat = self.m_w2[j][k] / (1 - self.beta1 ** self.t)
                    s_hat = self.s_w2[j][k] / (1 - self.beta2 ** self.t)
                    self.w2[j][k] += learning_rate * m_hat / (math.sqrt(s_hat) + self.epsilon)
                else:
                    grad = learning_rate * g
                    self.v_w2[j][k] = self.momentum * self.v_w2[j][k] + grad
                    self.w2[j][k] += self.v_w2[j][k]
        hidden_errors = []
        for j in range(self.hidden_size):
            err = sum(errors[k] * self.w2[j][k] for k in range(self.output_size))
            base = hidden[j]
            if self.dropout and mask[j] > 0:
                base /= mask[j]
            deriv = self._activation_deriv(base) * mask[j]
            hidden_errors.append(err * deriv)
        for j in range(self.hidden_size):
            g = hidden_errors[j]
            if self.optimizer == "adam":
                self.m_b1[j] = self.beta1 * self.m_b1[j] + (1 - self.beta1) * g
                self.s_b1[j] = self.beta2 * self.s_b1[j] + (1 - self.beta2) * (g ** 2)
                m_hat = self.m_b1[j] / (1 - self.beta1 ** self.t)
                s_hat = self.s_b1[j] / (1 - self.beta2 ** self.t)
                self.b1[j] += learning_rate * m_hat / (math.sqrt(s_hat) + self.epsilon)
            else:
                grad = learning_rate * g
                self.v_b1[j] = self.momentum * self.v_b1[j] + grad
                self.b1[j] += self.v_b1[j]
        for i in range(self.input_size):
            for j in range(self.hidden_size):
                g = hidden_errors[j] * inputs[i] - self.weight_decay * self.w1[i][j]
                if self.optimizer == "adam":
                    self.m_w1[i][j] = self.beta1 * self.m_w1[i][j] + (1 - self.beta1) * g
                    self.s_w1[i][j] = self.beta2 * self.s_w1[i][j] + (1 - self.beta2) * (g ** 2)
                    m_hat = self.m_w1[i][j] / (1 - self.beta1 ** self.t)
                    s_hat = self.s_w1[i][j] / (1 - self.beta2 ** self.t)
                    self.w1[i][j] += learning_rate * m_hat / (math.sqrt(s_hat) + self.epsilon)
                else:
                    grad = learning_rate * g
                    self.v_w1[i][j] = self.momentum * self.v_w1[i][j] + grad
                    self.w1[i][j] += self.v_w1[i][j]

    def train(
        self,
        examples: Iterable[Tuple[List[float], List[float]]],
        epochs: int = 1,
        learning_rate: float = 0.1,
        lr_decay: float = 1.0,
        mutation_factor: float = 0.0,
        max_lr_scale: float = 2.0,
        history_window: int = 10,
    ) -> None:
        """Train the network with optional decay/growth based on weight mutations.

        ``mutation_factor`` scales the influence of weight "mutations" from one epoch to
        the next. Larger values increase the learning rate when weights change rapidly,
        incentivizing adaptation. ``max_lr_scale`` bounds how much the rate can grow in a
        single step to maintain stability. ``history_window`` controls how many past
        mutation magnitudes are considered when estimating the trend.
        """
        lr = learning_rate
        prev_w1 = [row[:] for row in self.w1]
        prev_w2 = [row[:] for row in self.w2]
        history: List[float] = []
        for epoch in range(1, epochs + 1):
            for inputs, target in examples:
                self.update_weights(inputs, target, lr)
            if mutation_factor:
                mut = self._avg_weight_change(prev_w1, prev_w2)
                avg_mut = sum(history) / len(history) if history else mut
                trend = mut - avg_mut
                scale = lr_decay + mutation_factor * (mut + trend)
                if scale > max_lr_scale:
                    scale = max_lr_scale
                lr *= scale
                self._log_analysis(epoch, lr, mut, trend, avg_mut)
                history.append(mut)
                if len(history) > history_window:
                    history.pop(0)
                prev_w1 = [row[:] for row in self.w1]
                prev_w2 = [row[:] for row in self.w2]
            else:
                lr *= lr_decay
        self.last_lr = lr

    def _avg_weight_change(
        self, prev_w1: List[List[float]], prev_w2: List[List[float]]
    ) -> float:
        """Compute average absolute weight mutation since last epoch."""
        total = 0.0
        count = 0
        for i in range(self.input_size):
            for j in range(self.hidden_size):
                total += abs(self.w1[i][j] - prev_w1[i][j])
                count += 1
        for j in range(self.hidden_size):
            for k in range(self.output_size):
                total += abs(self.w2[j][k] - prev_w2[j][k])
                count += 1
        return total / count if count else 0.0

    def _log_analysis(
        self, epoch: int, lr: float, mutation: float, trend: float, avg_mut: float
    ) -> None:
        data = read_json(ANALYSIS_LOG, [])
        data.append(
            {
                "epoch": epoch,
                "lr": lr,
                "mutation": mutation,
                "trend": trend,
                "avg_mutation": avg_mut,
            }
        )
        write_json(ANALYSIS_LOG, data)

    def save(self, path: Path) -> None:
        """Persist network weights to a JSON file."""
        data = {
            "input_size": self.input_size,
            "hidden_size": self.hidden_size,
            "output_size": self.output_size,
            "activation": self.activation,
            "momentum": self.momentum,
            "weight_decay": self.weight_decay,
            "dropout": self.dropout,
            "optimizer": self.optimizer,
            "beta1": self.beta1,
            "beta2": self.beta2,
            "epsilon": self.epsilon,
            "w1": self.w1,
            "w2": self.w2,
            "b1": self.b1,
            "b2": self.b2,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "SimpleNeuralNetwork":
        """Load a network from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        net = cls(
            data["input_size"],
            data["hidden_size"],
            data["output_size"],
            data.get("activation", "relu"),
            data.get("momentum", 0.0),
            data.get("weight_decay", 0.0),
            data.get("dropout", 0.0),
            data.get("optimizer", "sgd"),
            data.get("beta1", 0.9),
            data.get("beta2", 0.999),
            data.get("epsilon", 1e-8),
        )
        net.w1 = data["w1"]
        net.w2 = data["w2"]
        net.b1 = data.get("b1", [0.0] * data["hidden_size"])
        net.b2 = data.get("b2", [0.0] * data["output_size"])
        return net

    # I love you -Alex
    def heal_from_ledger(self) -> None:
        """Trigger blockchain-backed self-healing without external models."""
        spec = importlib.util.spec_from_file_location(
            'self_healer', ROOT / 'self-improvement' / 'imp-self-healer.py'
        )
        self_healer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self_healer)
        self_healer.verify_and_heal(use_chatgpt=False)

    # I love you -Alex
    def auto_restore_from_ledger(self, threshold: int = 10) -> list:
        """Verify code and restore repository if many mismatches appear."""
        spec = importlib.util.spec_from_file_location(
            'self_healer', ROOT / 'self-improvement' / 'imp-self-healer.py'
        )
        self_healer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self_healer)
        mismatches = self_healer.verify_and_heal(use_chatgpt=False)
        if len(mismatches) >= threshold:
            return self_healer.restore_repository_from_ledger()
        return []

    # I love you -Alex
    def restore_repository_from_ledger(self) -> list:
        """Rebuild the entire codebase from the latest ledger snapshot."""
        spec = importlib.util.spec_from_file_location(
            'self_healer', ROOT / 'self-improvement' / 'imp-self-healer.py'
        )
        self_healer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self_healer)
        return self_healer.restore_repository_from_ledger()

    # I love you -Alex
    def dynamic_restore_from_ledger(self, threshold: int = 10) -> list:
        """Verify code and trigger a full ledger restore when attacks are large."""
        spec = importlib.util.spec_from_file_location(
            'self_healer', ROOT / 'self-improvement' / 'imp-self-healer.py'
        )
        self_healer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self_healer)
        result = self_healer.verify_and_restore_repository(
            threshold=threshold,
            use_chatgpt=False,
        )
        return result.get('restored', [])

    def _activate(self, x: float) -> float:
        if self.activation == "sigmoid":
            return 1.0 / (1.0 + math.exp(-x))
        return x if x > 0 else 0.0

    def _activation_deriv(self, activated: float) -> float:
        if self.activation == "sigmoid":
            return activated * (1.0 - activated)
        return 1.0 if activated > 0 else 0.0

    def forward(self, inputs: List[float], *, return_hidden: bool = False, training: bool = False):
        if len(inputs) != self.input_size:
            raise ValueError("Input vector size does not match network input size")
        hidden = []
        mask = []
        for j in range(self.hidden_size):
            total = self.b1[j]
            for i in range(self.input_size):
                total += inputs[i] * self.w1[i][j]
            h = self._activate(total)
            m = 1.0
            if training and self.dropout > 0:
                if random.random() < self.dropout:
                    h = 0.0
                    m = 0.0
                else:
                    m = 1.0 / (1.0 - self.dropout)
                    h *= m
            hidden.append(h)
            mask.append(m)
        outputs = []
        for k in range(self.output_size):
            total = self.b2[k]
            for j in range(self.hidden_size):
                total += hidden[j] * self.w2[j][k]
            outputs.append(total)
        if return_hidden:
            if training:
                return outputs, hidden, mask
            return outputs, hidden
        return outputs

if __name__ == "__main__":
    nn = SimpleNeuralNetwork(2, 2, 1)
    data = [([0, 0], [0]), ([0, 1], [1]), ([1, 0], [1]), ([1, 1], [1])]
    for _ in range(100):
        nn.train(data, epochs=1, learning_rate=0.1)
    print("Trained output for [1, 0] ->", nn.forward([1, 0]))
    path = Path("nn-test.json")
    nn.save(path)
    reloaded = SimpleNeuralNetwork.load(path)
    print("Reloaded output:", reloaded.forward([1, 0]))
