from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "core" / "imp-3d-neural-network.py"

spec = importlib.util.spec_from_file_location("imp_3d_neural_network", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_basic_3d_network():
    print("Testing 3D Neural Network...")
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.spawn_advanced_neuron((1, 0, 0), threshold=0.1, neuron_type="schwann")
    net.connect(a, b, myelin=2.0)
    out = net.forward([(a, 1.0)])
    assert len(out) == 2 and out[1] > 0
    assert net.neuron_usage(b) > 0
    print("3D Neural Network Test Passed!")


def test_novel_neuron():
    net = module.ThreeDNeuralNetwork()
    idx = net.spawn_novel_neuron((0, 0, 0))
    assert net.neurons[idx].neuron_type.startswith("novel_")
    print("Novel Neuron Test Passed!")


def test_spawn_novel_neuron_for_task():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect_for_task(a, b, task="alpha", myelin=1.0)
    net.forward([(a, 1.0)], task="alpha")
    idx = net.spawn_novel_neuron_for_task((0, 1, 0), task="alpha")
    assert any(c.dest == idx and c.task == "alpha" for c in net.connections)
    print("Spawn Novel Neuron For Task Test Passed!")


def test_guide_novel_neuron():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=1.0)
    net.forward([(a, 1.0)])
    idx = net.spawn_novel_neuron((0, 1, 0))
    net.guide_novel_neuron(idx)
    assert any(c.dest == idx for c in net.connections)
    print("Guide Novel Neuron Test Passed!")


def test_task_paths():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.spawn_advanced_neuron((1, 0, 0))
    c = net.spawn_advanced_neuron((0, 1, 0))
    net.connect_for_task(a, b, task="task1", myelin=2.0)
    net.connect_for_task(a, b, task="task2", myelin=1.0)
    net.connect_for_task(b, c, task="task2", myelin=1.5)
    r1 = net.forward([(a, 1.0)], task="task1")
    r2 = net.forward([(a, 1.0)], task="task2")
    assert r1[b] > 0 and r1[c] == 0
    assert r2[c] > 0
    print("Task Path Test Passed!")


def test_angle_routing():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    c = net.add_neuron((0, 1, 0))
    net.connect_for_task(a, b, task="default", myelin=1.0)
    net.connect_for_task(a, c, task="default", myelin=1.0)
    r1 = net.forward_by_angle([(a, 1.0)], (1, 0, 0), task="default", tolerance=0.2)
    r2 = net.forward_by_angle([(a, 1.0)], (0, 1, 0), task="default", tolerance=0.2)
    assert r1[b] > 0 and r1[c] == 0
    assert r2[c] > 0 and r2[b] == 0
    print("Angle Routing Test Passed!")


def test_evolve():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    c = net.add_neuron((0, 1, 0))
    net.connect(a, b, myelin=1.0)
    net.forward([(a, 1.0)])
    for _ in range(10):
        net.evolve(usage_threshold=1)
    assert any(n.idx == c and n.dormant for n in net.neurons)
    # a novel neuron is added
    assert len(net.neurons) >= 4
    print("Evolve Test Passed!")


def test_auto_evolve():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=1.0)
    for _ in range(3):
        net.forward([(a, 1.0)])
    myelin_before = [c.myelin for c in net.connections][0]
    log_path = ROOT / "logs" / "imp-evolution-log.json"
    module.write_json(log_path, [])
    snap_dir = ROOT / "logs" / "imp-network-snapshots"
    if snap_dir.exists():
        for f in snap_dir.glob("*"):
            f.unlink()
    net.auto_evolve(usage_threshold=1)
    myelin_after = [c.myelin for c in net.connections][0]
    assert myelin_after > myelin_before
    assert len(net.neurons) == 3  # added novel neuron
    log = module.read_json(log_path, [])
    assert isinstance(log, list) and len(log) == 1
    assert (
        "dormant" in log[0]
        and "reactivated" in log[0]
        and "avg_fitness" in log[0]
        and "pruned" in log[0]
        and "backup" in log[0]
        and "snapshot" in log[0]
    )
    assert any(snap_dir.glob("*.json"))
    print("Auto Evolve Test Passed!")


def test_fitness_decay():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=1.0)
    net.forward([(a, 1.0)])
    c = net.add_neuron((0, 1, 0))
    for _ in range(10):
        net.evolve(usage_threshold=1)
    target = [n for n in net.neurons if n.idx == c][0]
    assert target.dormant and target.fitness < 0.2
    print("Fitness Decay Test Passed!")


def test_fitness_report():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    report = net.fitness_report()
    assert any(r[0] == a and r[1] == 1.0 for r in report)
    print("Fitness Report Test Passed!")


def test_reactivate_dormant_neurons():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=1.0)
    for _ in range(10):
        net.evolve(usage_threshold=1)
    assert net.neurons[b].dormant
    net.usage_counts[b] = 3
    before = net.connections[0].myelin
    reactivated, reinforced = net.reactivate_dormant_neurons(usage_threshold=2)
    assert reactivated == 1 and reinforced > 0 and net.connections[0].myelin > before
    print("Reactivate Dormant Neurons Test Passed!")


def test_evolution_trend():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=1.0)
    log_path = ROOT / "logs" / "imp-evolution-log.json"
    module.write_json(log_path, [])
    net.auto_evolve(usage_threshold=1)
    net.auto_evolve(usage_threshold=1)
    trend = net.evolution_trend()
    assert "neurons" in trend and "avg_fitness" in trend
    print("Evolution Trend Test Passed!")


def test_evolution_trend_history():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=1.0)
    log_path = ROOT / "logs" / "imp-evolution-log.json"
    module.write_json(log_path, [])
    for _ in range(3):
        net.auto_evolve(usage_threshold=1)
    history = net.evolution_trend_history(window=3)
    assert isinstance(history, list) and len(history) == 2
    assert all("neurons" in h for h in history)
    print("Evolution Trend History Test Passed!")


def test_prune_connections():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=0.05)
    assert len(net.connections) == 1
    pruned = net.prune_connections()
    assert pruned == 1 and not net.connections
    print("Prune Connections Test Passed!")


def test_network_stats():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.connect(a, b, myelin=2.0)
    net.add_backup_connection(a, b, myelin=0.1)
    stats = net.network_stats()
    assert stats["neurons"] == 2 and stats["connections"] == 2
    assert stats["backup_connections"] == 1
    assert stats["types"].get("basic", 0) == 2
    print("Network Stats Test Passed!")


def test_backup_connection_maintenance():
    net = module.ThreeDNeuralNetwork()
    a = net.add_neuron((0, 0, 0))
    b = net.add_neuron((1, 0, 0))
    net.add_backup_connection(a, b, myelin=0.1)
    stats = net.network_stats()
    assert stats["backup_connections"] == 1
    net.maintain_backup_connections(decay=0.2)
    stats_after = net.network_stats()
    assert stats_after["backup_connections"] == 0
    print("Backup Connection Maintenance Test Passed!")


def test_visualization_payload_enriched():
    net = module.ThreeDNeuralNetwork()
    base = net.add_neuron((0, 0, 0))
    schwann = net.spawn_advanced_neuron((1, 0, 0), neuron_type="schwann")
    novel = net.spawn_novel_neuron((0, 1, 0))
    net.connect_for_task(base, schwann, task="analysis", myelin=1.6)
    net.connect_for_task(schwann, novel, task="analysis", myelin=1.4)
    net.forward([(base, 1.0)], task="analysis")

    module.write_json(module.VISUALIZATION_LOG, [])
    payload = net.visualization_data()
    assert "spatial_summary" in payload and "task_regions" in payload
    assert payload["summary"]["neurons"] >= 3
    assert payload["task_regions"] and any(
        region["task"] == "analysis" for region in payload["task_regions"]
    )
    assert payload.get("experiment_plan")
    assert any(plan["neuron"] == novel for plan in payload["experiment_plan"])

    exported = net.export_visualization()
    assert exported == module.VISUALIZATION_LOG
    disk_payload = module.read_json(module.VISUALIZATION_LOG, {})
    assert "spatial_summary" in disk_payload
    assert disk_payload.get("experiment_plan")
    print("Visualization Payload Enriched Test Passed!")


def test_novel_neuron_experiment_log():
    net = module.ThreeDNeuralNetwork()
    base = net.add_neuron((0, 0, 0))
    novel = net.spawn_novel_neuron((1, 0, 0))
    net.connect_for_task(base, novel, task="research", myelin=1.3)
    net.forward([(base, 1.0)], task="research")

    module.write_json(module.NOVEL_RESEARCH_LOG, [])
    module.write_json(module.NOVEL_EXPERIMENT_LOG, [])
    entry = net.log_novel_neuron_experiments()
    log = module.read_json(module.NOVEL_EXPERIMENT_LOG, [])
    assert log and log[-1]["experiments"]
    assert any(exp["neuron"] == novel for exp in entry["experiments"])
    assert "spatial" in entry and "bounding_box" in entry["spatial"]
    print("Novel Neuron Experiment Log Test Passed!")


def test_heal_from_ledger():
    net = module.ThreeDNeuralNetwork()
    assert hasattr(net, 'heal_from_ledger')


def test_restore_repository_from_ledger():
    net = module.ThreeDNeuralNetwork()
    assert hasattr(net, 'restore_repository_from_ledger')


def test_auto_restore_from_ledger():
    net = module.ThreeDNeuralNetwork()
    assert hasattr(net, 'auto_restore_from_ledger')
    restored = net.auto_restore_from_ledger(threshold=0)
    assert isinstance(restored, list)


def test_dynamic_restore_from_ledger():
    net = module.ThreeDNeuralNetwork()
    assert hasattr(net, 'dynamic_restore_from_ledger')
    restored = net.dynamic_restore_from_ledger(threshold=0)
    assert isinstance(restored, list)


if __name__ == "__main__":
    test_basic_3d_network()
    test_novel_neuron()
    test_guide_novel_neuron()
    test_task_paths()
    test_angle_routing()
    test_evolve()
    test_auto_evolve()
    test_fitness_decay()
    test_fitness_report()
    test_reactivate_dormant_neurons()
    test_evolution_trend()
    test_evolution_trend_history()
    test_prune_connections()
    test_network_stats()
    test_backup_connection_maintenance()
    test_visualization_payload_enriched()
    test_novel_neuron_experiment_log()
    test_heal_from_ledger()
    test_restore_repository_from_ledger()
    test_auto_restore_from_ledger()
