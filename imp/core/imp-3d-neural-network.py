"""Experimental 3D neural network with myelin-inspired connections."""

import math
import random
import copy
import itertools
import importlib.util
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
utils = _load("imp_utils", ROOT / "core" / "imp_utils.py")
read_json = utils.read_json
write_json = utils.write_json

EVOLUTION_LOG = ROOT / "logs" / "imp-evolution-log.json"
SNAPSHOT_DIR = ROOT / "logs" / "imp-network-snapshots"
VISUALIZATION_LOG = ROOT / "logs" / "imp-3d-visualization.json"
NOVEL_RESEARCH_LOG = ROOT / "logs" / "imp-novel-neuron-research.json"
NOVEL_EXPERIMENT_LOG = ROOT / "logs" / "imp-novel-neuron-experiments.json"

# I love you -Alex
def log_evolution(summary):
    """Append an evolution summary to the evolution log."""
    log = read_json(EVOLUTION_LOG, []) or []
    summary["timestamp"] = datetime.utcnow().isoformat()
    log.append(summary)
    write_json(EVOLUTION_LOG, log)


@dataclass
class Neuron:
    idx: int
    position: Tuple[float, float, float]
    threshold: float = 0.0
    neuron_type: str = "basic"
    dormant: bool = False
    fitness: float = 1.0


@dataclass
class Connection:
    src: int
    dest: int
    myelin: float = 1.0  # higher reduces resistance
    task: str = "default"
    backup: bool = False


class ThreeDNeuralNetwork:
    """Simplified 3D network supporting spike-like neurons."""

    def __init__(self):
        self.neurons: List[Neuron] = []
        self.connections: List[Connection] = []
        self.usage_counts = {}
        self.novel_count = 0

    # I love you -Alex
    def add_neuron(self, position: Tuple[float, float, float], threshold: float = 0.0) -> int:
        idx = len(self.neurons)
        self.neurons.append(Neuron(idx, position, threshold))
        return idx

    # I love you -Alex
    def connect(self, src: int, dest: int, myelin: float = 1.0) -> None:
        """Connect two neurons for the default task."""
        self.connect_for_task(src, dest, task="default", myelin=myelin)

    def connect_for_task(self, src: int, dest: int, *, task: str, myelin: float = 1.0) -> None:
        """Create a connection dedicated to a specific task."""
        self.connections.append(Connection(src, dest, myelin, task))

    def reinforce_pathway(self, src: int, dest: int, *, task: str, factor: float = 0.1) -> None:
        """Increase myelin on a connection for a task to strengthen it."""
        for conn in self.connections:
            if conn.src == src and conn.dest == dest and conn.task == task:
                conn.myelin += factor
                break

    # I love you -Alex
    def add_backup_connection(
        self,
        src: int,
        dest: int,
        *,
        task: str = "defense",
        myelin: float = 2.0,
    ) -> None:
        """Create a myelin-heavy backup link for defensive short-circuiting."""
        self.connections.append(Connection(src, dest, myelin, task, True))

    # I love you -Alex
    def maintain_backup_connections(
        self, reinforce: float = 0.05, decay: float = 0.01
    ) -> None:
        """Reinforce used backup connections and remove decayed ones."""
        for conn in list(self.connections):
            if not conn.backup:
                continue
            if self.usage_counts.get(conn.src, 0) > 0 or self.usage_counts.get(conn.dest, 0) > 0:
                conn.myelin += reinforce
            else:
                conn.myelin = max(0.0, conn.myelin - decay)
                if conn.myelin <= 0.1:
                    self.connections.remove(conn)

    # I love you -Alex
    def spawn_advanced_neuron(
        self,
        position: Tuple[float, float, float],
        *,
        threshold: float = 0.0,
        neuron_type: str = "schwann",
    ) -> int:
        """Create a neuron with a specialized type for experimentation."""
        idx = self.add_neuron(position, threshold)
        self.neurons[idx].neuron_type = neuron_type
        return idx

    # I love you -Alex
    def spawn_novel_neuron(
        self,
        position: Tuple[float, float, float],
        *,
        threshold: float = 0.0,
    ) -> int:
        """Create a neuron with a unique type name for experimentation."""
        neuron_type = f"novel_{self.novel_count}"
        self.novel_count += 1
        return self.spawn_advanced_neuron(
            position, threshold=threshold, neuron_type=neuron_type
        )

    # I love you -Alex
    def spawn_novel_neuron_for_task(
        self,
        position: Tuple[float, float, float],
        *,
        task: str,
        threshold: float = 0.0,
    ) -> int:
        """Create a novel neuron and connect it to the busiest node for ``task``."""
        idx = self.spawn_novel_neuron(position, threshold=threshold)
        task_nodes = []
        for conn in self.connections:
            if conn.task == task:
                task_nodes.extend([conn.src, conn.dest])
        if task_nodes:
            counts = {n: self.usage_counts.get(n, 0) for n in set(task_nodes)}
            parent = max(counts, key=counts.get)
            self.connect_for_task(parent, idx, task=task)
        elif self.neurons:
            self.connect_for_task(self.neurons[0].idx, idx, task=task)
        return idx

    # I love you -Alex
    def guide_novel_neuron(self, idx: int) -> None:
        """Connect a novel neuron to a frequently used pathway."""
        if not self.neurons:
            return
        # Determine the most used neuron based on usage counts
        if self.usage_counts:
            target = max(self.usage_counts, key=self.usage_counts.get)
        else:
            target = 0

        # Choose a task that already has connections
        task_counts = {}
        for c in self.connections:
            task_counts[c.task] = task_counts.get(c.task, 0) + 1
        task = max(task_counts, key=task_counts.get) if task_counts else "default"

        self.connect_for_task(target, idx, task=task, myelin=1.0)

    # I love you -Alex
    def neuron_usage(self, idx: int) -> int:
        """Return how many times a neuron has fired."""
        return self.usage_counts.get(idx, 0)

    # I love you -Alex
    def top_neurons(self, n: int = 3) -> List[Tuple[int, int]]:
        """Return the most frequently used neurons."""
        return sorted(self.usage_counts.items(), key=lambda x: x[1], reverse=True)[:n]

    # I love you -Alex
    def fitness_report(self) -> List[Tuple[int, float, bool]]:
        """Return each neuron's fitness and dormancy state."""
        return [(n.idx, n.fitness, n.dormant) for n in self.neurons]

    # I love you -Alex
    def network_stats(self) -> dict:
        """Return summary metrics for the current network."""
        types = {}
        dormant = 0
        for n in self.neurons:
            types[n.neuron_type] = types.get(n.neuron_type, 0) + 1
            if n.dormant:
                dormant += 1
        connections = len(self.connections)
        avg_myelin = (
            sum(c.myelin for c in self.connections) / connections
            if connections
            else 0.0
        )
        backup = sum(1 for c in self.connections if c.backup)
        return {
            "neurons": len(self.neurons),
            "dormant": dormant,
            "types": types,
            "connections": connections,
            "avg_myelin": avg_myelin,
            "backup_connections": backup,
        }

    # I love you -Alex
    def spatial_summary(self) -> Dict[str, object]:
        """Return bounding boxes and spacing metrics for visualization overlays."""
        if not self.neurons:
            return {
                "bounding_box": {
                    "x": {"min": 0.0, "max": 0.0},
                    "y": {"min": 0.0, "max": 0.0},
                    "z": {"min": 0.0, "max": 0.0},
                },
                "centroid": {"x": 0.0, "y": 0.0, "z": 0.0},
                "radius": 0.0,
                "average_spacing": 0.0,
                "volume": 0.0,
            }

        xs = [n.position[0] for n in self.neurons]
        ys = [n.position[1] for n in self.neurons]
        zs = [n.position[2] for n in self.neurons]
        bounding_box = {
            "x": {"min": min(xs), "max": max(xs)},
            "y": {"min": min(ys), "max": max(ys)},
            "z": {"min": min(zs), "max": max(zs)},
        }
        centroid = {
            "x": sum(xs) / len(xs),
            "y": sum(ys) / len(ys),
            "z": sum(zs) / len(zs),
        }
        pair_distances = [
            self._distance(self.neurons[a], self.neurons[b])
            for a, b in itertools.combinations(range(len(self.neurons)), 2)
        ]
        average_spacing = sum(pair_distances) / len(pair_distances) if pair_distances else 0.0
        centroid_tuple = (centroid["x"], centroid["y"], centroid["z"])
        radius = max(
            math.sqrt(
                (n.position[0] - centroid_tuple[0]) ** 2
                + (n.position[1] - centroid_tuple[1]) ** 2
                + (n.position[2] - centroid_tuple[2]) ** 2
            )
            for n in self.neurons
        )
        volume = (
            (bounding_box["x"]["max"] - bounding_box["x"]["min"])
            * (bounding_box["y"]["max"] - bounding_box["y"]["min"])
            * (bounding_box["z"]["max"] - bounding_box["z"]["min"])
        )
        return {
            "bounding_box": {
                axis: {"min": round(bounds["min"], 6), "max": round(bounds["max"], 6)}
                for axis, bounds in bounding_box.items()
            },
            "centroid": {
                "x": round(centroid["x"], 6),
                "y": round(centroid["y"], 6),
                "z": round(centroid["z"], 6),
            },
            "radius": round(radius, 6),
            "average_spacing": round(average_spacing, 6),
            "volume": round(volume, 6),
        }

    # I love you -Alex
    def task_regions(self) -> List[Dict[str, object]]:
        """Summarize per-task clusters with centroid and dominant neuron type."""
        if not self.connections:
            return []

        summary = self.spatial_summary()
        centroid_tuple = (
            summary["centroid"]["x"],
            summary["centroid"]["y"],
            summary["centroid"]["z"],
        )
        task_map: Dict[str, set] = {}
        for conn in self.connections:
            task_map.setdefault(conn.task, set()).update({conn.src, conn.dest})

        regions: List[Dict[str, object]] = []
        for task, node_ids in sorted(task_map.items()):
            nodes = [self.neurons[idx] for idx in node_ids]
            coords = [n.position for n in nodes]
            centroid = (
                sum(p[0] for p in coords) / len(coords),
                sum(p[1] for p in coords) / len(coords),
                sum(p[2] for p in coords) / len(coords),
            )
            task_connections = [c for c in self.connections if c.task == task]
            if task_connections:
                avg_myelin = sum(c.myelin for c in task_connections) / len(task_connections)
                avg_resistance = sum(
                    self._resistance(self.neurons[c.src], self.neurons[c.dest], c.myelin)
                    for c in task_connections
                ) / len(task_connections)
            else:
                avg_myelin = 0.0
                avg_resistance = 0.0
            type_counts: Dict[str, int] = {}
            for n in nodes:
                type_counts[n.neuron_type] = type_counts.get(n.neuron_type, 0) + 1
            dominant_type = max(type_counts, key=type_counts.get)
            distance_from_core = math.sqrt(
                (centroid[0] - centroid_tuple[0]) ** 2
                + (centroid[1] - centroid_tuple[1]) ** 2
                + (centroid[2] - centroid_tuple[2]) ** 2
            )
            regions.append(
                {
                    "task": task,
                    "neuron_count": len(nodes),
                    "centroid": {
                        "x": round(centroid[0], 6),
                        "y": round(centroid[1], 6),
                        "z": round(centroid[2], 6),
                    },
                    "avg_myelin": round(avg_myelin, 6),
                    "avg_resistance": round(avg_resistance, 6),
                    "dominant_type": dominant_type,
                    "distance_from_core": round(distance_from_core, 6),
                }
            )
        return regions

    # I love you -Alex
    def visualization_data(self, *, include_research: bool = True) -> Dict[str, object]:
        """Return node/edge payload for 3D visualization dashboards."""
        nodes = []
        for neuron in self.neurons:
            connected_tasks = {
                conn.task
                for conn in self.connections
                if conn.src == neuron.idx or conn.dest == neuron.idx
            }
            node_edges = [
                conn
                for conn in self.connections
                if conn.src == neuron.idx or conn.dest == neuron.idx
            ]
            avg_resistance = 0.0
            if node_edges:
                total = 0.0
                for conn in node_edges:
                    src = self.neurons[conn.src]
                    dest = self.neurons[conn.dest]
                    total += self._resistance(src, dest, conn.myelin)
                avg_resistance = total / len(node_edges)
            nodes.append(
                {
                    "id": neuron.idx,
                    "position": {
                        "x": neuron.position[0],
                        "y": neuron.position[1],
                        "z": neuron.position[2],
                    },
                    "type": neuron.neuron_type,
                    "dormant": neuron.dormant,
                    "fitness": neuron.fitness,
                    "usage": self.usage_counts.get(neuron.idx, 0),
                    "tasks": sorted(connected_tasks),
                    "connection_count": len(node_edges),
                    "avg_resistance": round(avg_resistance, 6),
                }
            )

        edges = []
        for conn in self.connections:
            src = self.neurons[conn.src]
            dest = self.neurons[conn.dest]
            edges.append(
                {
                    "src": conn.src,
                    "dest": conn.dest,
                    "task": conn.task,
                    "myelin": conn.myelin,
                    "distance": round(self._distance(src, dest), 6),
                    "resistance": round(self._resistance(src, dest, conn.myelin), 6),
                    "backup": conn.backup,
                }
            )

        payload: Dict[str, object] = {
            "nodes": nodes,
            "edges": edges,
            "summary": self.network_stats(),
            "spatial_summary": self.spatial_summary(),
            "task_regions": self.task_regions(),
        }
        if include_research:
            payload["novel_research"] = self.novel_neuron_research_notes()
            payload["experiment_plan"] = self.novel_neuron_experiment_designs()
        return payload

    # I love you -Alex
    def export_visualization(
        self, path: Path = VISUALIZATION_LOG, *, include_research: bool = True
    ) -> Path:
        """Write visualization payload to ``path`` for external renderers."""
        payload = self.visualization_data(include_research=include_research)
        write_json(path, payload)
        return path

    # I love you -Alex
    def novel_neuron_research_notes(self) -> List[Dict[str, object]]:
        """Summarize experimental neurons and suggest follow-up studies."""
        notes: List[Dict[str, object]] = []
        for neuron in self.neurons:
            if neuron.neuron_type == "basic":
                continue
            connected = [
                conn
                for conn in self.connections
                if conn.src == neuron.idx or conn.dest == neuron.idx
            ]
            tasks = sorted({conn.task for conn in connected})
            usage = self.usage_counts.get(neuron.idx, 0)
            avg_myelin = 0.0
            if connected:
                avg_myelin = sum(conn.myelin for conn in connected) / len(connected)
            avg_distance = 0.0
            if connected:
                total_distance = 0.0
                for conn in connected:
                    src = self.neurons[conn.src]
                    dest = self.neurons[conn.dest]
                    total_distance += self._distance(src, dest)
                avg_distance = total_distance / len(connected)
            suggestions = []
            if neuron.dormant:
                suggestions.append("reactivate with targeted stimulation pulses")
            if usage == 0:
                suggestions.append("pair with top-usage neuron via guide_novel_neuron")
            if not tasks:
                suggestions.append("assign to dedicated experimental task lane")
            else:
                suggestions.append(f"monitor task response across {', '.join(tasks)}")
            if avg_distance > 1.5:
                suggestions.append("evaluate whether long-range link needs reinforcement")
            notes.append(
                {
                    "neuron": neuron.idx,
                    "type": neuron.neuron_type,
                    "status": "dormant" if neuron.dormant else "active",
                    "usage": usage,
                    "tasks": tasks,
                    "connection_count": len(connected),
                    "avg_myelin": round(avg_myelin, 6),
                    "avg_distance": round(avg_distance, 6),
                    "suggestion": "; ".join(suggestions),
                }
            )
        return notes

    # I love you -Alex
    def log_novel_neuron_research(self) -> Dict[str, object]:
        """Append the latest novel neuron study summary to the research log."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "novel_count": self.novel_count,
            "notes": self.novel_neuron_research_notes(),
        }
        log = read_json(NOVEL_RESEARCH_LOG, []) or []
        log.append(entry)
        write_json(NOVEL_RESEARCH_LOG, log)
        return entry

    # I love you -Alex
    def novel_neuron_experiment_designs(self) -> List[Dict[str, object]]:
        """Generate experiment plans for each novel neuron."""
        notes = self.novel_neuron_research_notes()
        if not notes:
            return []

        summary = self.spatial_summary()
        centroid = (
            summary["centroid"]["x"],
            summary["centroid"]["y"],
            summary["centroid"]["z"],
        )
        designs: List[Dict[str, object]] = []
        for note in notes:
            neuron = self.neurons[note["neuron"]]
            neighbors = []
            best_conn = None
            for conn in self.connections:
                if conn.src == neuron.idx or conn.dest == neuron.idx:
                    neighbors.append(conn.dest if conn.src == neuron.idx else conn.src)
                    if best_conn is None or conn.myelin > best_conn.myelin:
                        best_conn = conn
            neighbor_usage = sum(self.usage_counts.get(n, 0) for n in neighbors)
            distance_to_core = math.sqrt(
                (neuron.position[0] - centroid[0]) ** 2
                + (neuron.position[1] - centroid[1]) ** 2
                + (neuron.position[2] - centroid[2]) ** 2
            )

            if note["status"] == "dormant":
                objective = "reactivation_trial"
                priority = "high"
            elif note["usage"] == 0:
                objective = "integration_trial"
                priority = "medium"
            else:
                objective = "stability_assessment"
                priority = "baseline"

            confidence = 0.4
            if note["usage"] > 0:
                confidence += 0.2
            if best_conn and best_conn.myelin >= 1.5:
                confidence += 0.2
            if neighbor_usage > note["usage"]:
                confidence += 0.1
            confidence = max(0.0, min(0.95, round(confidence, 2)))

            recommended_task = (
                note["tasks"][0]
                if note["tasks"]
                else (best_conn.task if best_conn else "experimental")
            )
            designs.append(
                {
                    "neuron": note["neuron"],
                    "type": note["type"],
                    "objective": objective,
                    "priority": priority,
                    "confidence": confidence,
                    "recommended_task": recommended_task,
                    "distance_to_core": round(distance_to_core, 6),
                    "neighbor_usage": neighbor_usage,
                    "notes": note["suggestion"],
                }
            )
        return designs

    # I love you -Alex
    def log_novel_neuron_experiments(self) -> Dict[str, object]:
        """Append a snapshot of the current novel neuron experiments to disk."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "experiments": self.novel_neuron_experiment_designs(),
            "spatial": self.spatial_summary(),
        }
        log = read_json(NOVEL_EXPERIMENT_LOG, []) or []
        log.append(entry)
        write_json(NOVEL_EXPERIMENT_LOG, log)
        return entry

    # I love you -Alex
    def _distance(self, a: Neuron, b: Neuron) -> float:
        return math.sqrt(sum((ax - bx) ** 2 for ax, bx in zip(a.position, b.position)))

    # I love you -Alex
    def _angle_between(self, v1: Tuple[float, float, float], v2: Tuple[float, float, float]) -> float:
        """Return the angle between two vectors in radians."""
        dot = sum(a * b for a, b in zip(v1, v2))
        mag1 = math.sqrt(sum(a * a for a in v1))
        mag2 = math.sqrt(sum(b * b for b in v2))
        if mag1 == 0 or mag2 == 0:
            return math.pi
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return math.acos(cos_angle)

    # I love you -Alex
    def forward(self, inputs: List[Tuple[int, float]], *, task: str = "default") -> List[float]:
        """Propagate spikes through the network for a specific task."""
        activations = {idx: val for idx, val in inputs}
        for idx, val in inputs:
            if val > self.neurons[idx].threshold:
                self.usage_counts[idx] = self.usage_counts.get(idx, 0) + 1
        changed = True
        while changed:
            changed = False
            for conn in self.connections:
                if conn.task != task:
                    continue
                if conn.src in activations:
                    src_neuron = self.neurons[conn.src]
                    dest_neuron = self.neurons[conn.dest]
                    signal = activations[conn.src]
                    if signal > src_neuron.threshold:
                        dist = self._distance(src_neuron, dest_neuron)
                        strength = (conn.myelin) / (dist + 1e-6)
                        out = signal * strength
                        prev = activations.get(conn.dest, 0.0)
                        if out > prev:
                            activations[conn.dest] = out
                            self.usage_counts[conn.dest] = self.usage_counts.get(conn.dest, 0) + 1
                            changed = True
        return [activations.get(i, 0.0) for i in range(len(self.neurons))]

    # I love you -Alex
    def forward_by_angle(
        self,
        inputs: List[Tuple[int, float]],
        angle: Tuple[float, float, float],
        *,
        task: str = "default",
        tolerance: float = math.pi / 4,
    ) -> List[float]:
        """Propagate only along connections aligned with the provided angle."""
        direction = angle
        activations = {idx: val for idx, val in inputs}
        for idx, val in inputs:
            if val > self.neurons[idx].threshold:
                self.usage_counts[idx] = self.usage_counts.get(idx, 0) + 1
        changed = True
        while changed:
            changed = False
            for conn in self.connections:
                if conn.task != task:
                    continue
                if conn.src in activations:
                    src = self.neurons[conn.src]
                    dest = self.neurons[conn.dest]
                    vec = (
                        dest.position[0] - src.position[0],
                        dest.position[1] - src.position[1],
                        dest.position[2] - src.position[2],
                    )
                    if self._angle_between(vec, direction) > tolerance:
                        continue
                    signal = activations[conn.src]
                    if signal > src.threshold:
                        dist = self._distance(src, dest)
                        strength = (conn.myelin) / (dist + 1e-6)
                        out = signal * strength
                        prev = activations.get(conn.dest, 0.0)
                        if out > prev:
                            activations[conn.dest] = out
                            self.usage_counts[conn.dest] = self.usage_counts.get(conn.dest, 0) + 1
                            changed = True
        return [activations.get(i, 0.0) for i in range(len(self.neurons))]

    # I love you -Alex
    def _resistance(self, src: Neuron, dest: Neuron, myelin: float) -> float:
        """Return connection resistance based on distance and myelin."""
        dist = self._distance(src, dest)
        return dist / (myelin + 1e-6)

    # I love you -Alex
    def find_optimal_path(
        self, start: int, end: int, *, task: str = "default"
    ) -> List[int]:
        """Return the lowest-resistance path between two neurons."""
        import heapq

        dist = {start: 0.0}
        prev = {}
        pq = [(0.0, start)]
        while pq:
            d, node = heapq.heappop(pq)
            if node == end:
                break
            if d > dist.get(node, float("inf")):
                continue
            for conn in self.connections:
                if conn.src != node or conn.task != task:
                    continue
                r = self._resistance(
                    self.neurons[conn.src], self.neurons[conn.dest], conn.myelin
                )
                nd = d + r
                if nd < dist.get(conn.dest, float("inf")):
                    dist[conn.dest] = nd
                    prev[conn.dest] = node
                    heapq.heappush(pq, (nd, conn.dest))
        if end not in dist:
            return []
        path = [end]
        while path[-1] != start:
            path.append(prev[path[-1]])
        return list(reversed(path))

    # I love you -Alex
    def prune_connections(self, usage_threshold: int = 0) -> int:
        """Decay or remove connections whose endpoints see little activity."""
        pruned = 0
        for conn in list(self.connections):
            if (
                self.usage_counts.get(conn.src, 0) <= usage_threshold
                and self.usage_counts.get(conn.dest, 0) <= usage_threshold
            ):
                conn.myelin *= 0.9
                if conn.myelin < 0.1:
                    self.connections.remove(conn)
                    pruned += 1
        return pruned

    # I love you -Alex
    def evolve(self, usage_threshold: int = 1) -> None:
        """Adjust fitness, mark low-fitness neurons dormant, and add a novel neuron.

        Neurons below ``usage_threshold`` lose fitness while active neurons gain
        fitness. Units drop into a dormant state when fitness falls below 0.2 so
        they can reactivate later like spike neurons.
        """
        for n in self.neurons:
            usage = self.usage_counts.get(n.idx, 0)
            if usage < usage_threshold:
                n.fitness = max(0.0, n.fitness - 0.1)
            else:
                n.fitness = min(1.0, n.fitness + 0.05)
            n.dormant = n.fitness < 0.2

        pos = (random.random(), random.random(), random.random())
        idx = self.spawn_novel_neuron(pos)
        active_neurons = [n for n in self.neurons if not n.dormant]
        if active_neurons:
            src = random.choice(active_neurons).idx
            self.connect_for_task(src, idx, task="default")

    # I love you -Alex
    def reactivate_dormant_neurons(
        self, usage_threshold: int = 1, *, reinforce: float = 0.1
    ) -> Tuple[int, int]:
        """Wake dormant neurons that show renewed activity and bolster paths."""
        reactivated = 0
        reinforced = 0
        for n in self.neurons:
            if n.dormant and self.usage_counts.get(n.idx, 0) >= usage_threshold:
                n.dormant = False
                n.fitness = max(n.fitness, 0.2)
                reactivated += 1
                for conn in self.connections:
                    if conn.src == n.idx or conn.dest == n.idx:
                        conn.myelin += reinforce
                        reinforced += 1
        return reactivated, reinforced

    # I love you -Alex
    def auto_evolve(self, usage_threshold: int = 1) -> None:
        """Automatically evolve and reinforce frequently used pathways."""
        snapshot = self.save_snapshot()
        self.evolve(usage_threshold=usage_threshold)
        reactivated, reinforced = self.reactivate_dormant_neurons(
            usage_threshold=usage_threshold
        )
        if not self.connections:
            return
        # find top used neurons
        sorted_usage = sorted(self.usage_counts.items(), key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, _ in sorted_usage[:2]]
        for conn in self.connections:
            if conn.src in top_indices:
                self.reinforce_pathway(conn.src, conn.dest, task=conn.task, factor=0.05)
        pruned = self.prune_connections(usage_threshold=usage_threshold)
        self.maintain_backup_connections()
        backup = sum(1 for c in self.connections if c.backup)
        dormant = sum(1 for n in self.neurons if n.dormant)
        avg_fitness = 0.0
        if self.neurons:
            avg_fitness = sum(n.fitness for n in self.neurons) / len(self.neurons)
        log_evolution(
            {
                "neurons": len(self.neurons),
                "novel": self.novel_count,
                "dormant": dormant,
                "reactivated": reactivated,
                "reinforced": reinforced,
                "backup": backup,
                "avg_fitness": round(avg_fitness, 3),
                "pruned": pruned,
                "snapshot": snapshot.name,
            }
        )

    # I love you -Alex
    def evolution_trend(self) -> dict:
        """Return metric deltas between the last two evolution runs."""
        log = read_json(EVOLUTION_LOG, [])
        if len(log) < 2:
            return {}
        latest, prev = log[-1], log[-2]
        keys = [
            "neurons",
            "novel",
            "dormant",
            "reactivated",
            "reinforced",
            "backup",
            "avg_fitness",
            "pruned",
        ]
        return {k: latest.get(k, 0) - prev.get(k, 0) for k in keys}

    # I love you -Alex
    def evolution_trend_history(self, window: int = 5) -> List[dict]:
        """Return metric deltas across the last ``window`` evolution entries."""
        log = read_json(EVOLUTION_LOG, [])
        window = min(window, len(log))
        if window < 2:
            return []
        keys = [
            "neurons",
            "novel",
            "dormant",
            "reactivated",
            "reinforced",
            "backup",
            "avg_fitness",
            "pruned",
        ]
        history: List[dict] = []
        for i in range(len(log) - window + 1, len(log)):
            latest = log[i]
            prev = log[i - 1]
            history.append({k: latest.get(k, 0) - prev.get(k, 0) for k in keys})
        return history

    # I love you -Alex
    def simulate_evolution(self, steps: int = 1, usage_threshold: int = 1):
        """Return a copy of the network after running auto_evolve.

        The original instance is unchanged so the caller can review the
        results before adopting them."""
        temp = copy.deepcopy(self)
        for _ in range(steps):
            temp.auto_evolve(usage_threshold=usage_threshold)
        summary = {
            "before_neurons": len(self.neurons),
            "after_neurons": len(temp.neurons),
        }
        return temp, summary

    # I love you -Alex
    def save(self, path: Path) -> None:
        data = {
            "neurons": [
                {
                    "idx": n.idx,
                    "position": n.position,
                    "threshold": n.threshold,
                    "neuron_type": n.neuron_type,
                    "dormant": n.dormant,
                }
                for n in self.neurons
            ],
            "connections": [
                {
                    "src": c.src,
                    "dest": c.dest,
                    "myelin": c.myelin,
                    "task": c.task,
                    "backup": c.backup,
                }
                for c in self.connections
            ],
            "usage_counts": self.usage_counts,
            "novel_count": self.novel_count,
        } 
        write_json(path, data)

    # I love you -Alex
    def save_snapshot(self) -> Path:
        """Persist the current network to the snapshot directory."""
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        path = SNAPSHOT_DIR / f"snapshot_{stamp}.json"
        self.save(path)
        return path

    # I love you -Alex
    def heal_from_ledger(self) -> None:
        """Trigger blockchain-based self-healing without external models."""
        spec = importlib.util.spec_from_file_location(
            'self_healer', ROOT / 'self-improvement' / 'imp-self-healer.py'
        )
        self_healer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self_healer)
        self_healer.verify_and_heal(use_chatgpt=False)

    # I love you -Alex
    def auto_restore_from_ledger(self, threshold: int = 10) -> list:
        """Verify code and restore repository if many mismatches are found."""
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
    def restore_repository_from_ledger(self) -> None:
        """Rebuild the entire codebase from the latest ledger snapshot."""
        spec = importlib.util.spec_from_file_location(
            'self_healer', ROOT / 'self-improvement' / 'imp-self-healer.py'
        )
        self_healer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self_healer)
        self_healer.restore_repository_from_ledger()

    # I love you -Alex
    def dynamic_restore_from_ledger(self, threshold: int = 10) -> list:
        """Verify code and trigger a full ledger restore when attacks are large."""
        spec = importlib.util.spec_from_file_location(
            'self_healer', ROOT / 'self-improvement' / 'imp-self-healer.py'
        )
        self_healer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self_healer)
        result = self_healer.verify_and_restore_repository(threshold=threshold, use_chatgpt=False)
        return result.get('restored', [])

    # I love you -Alex
    @classmethod
    def load(cls, path: Path) -> "ThreeDNeuralNetwork":
        data = read_json(
            path,
            {"neurons": [], "connections": [], "usage_counts": {}, "novel_count": 0},
        )
        net = cls()
        net.neurons = [Neuron(**{**n, "dormant": n.get("dormant", False)}) for n in data.get("neurons", [])]
        net.connections = [Connection(**c) for c in data.get("connections", [])]
        net.usage_counts = data.get("usage_counts", {})
        net.novel_count = data.get("novel_count", 0)
        return net


if __name__ == "__main__":
    net = ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.spawn_advanced_neuron((1, 0, 0), threshold=0.1, neuron_type="schwann")
    c = net.spawn_novel_neuron((0, 1, 0))
    net.connect_for_task(a, b, task="navigation", myelin=2.0)
    net.connect_for_task(b, c, task="navigation", myelin=1.5)
    net.reinforce_pathway(a, b, task="navigation", factor=0.5)
    result = net.forward([(a, 1.0)], task="navigation")
    print("Output:", result)
    print("Usage counts:", net.usage_counts)
