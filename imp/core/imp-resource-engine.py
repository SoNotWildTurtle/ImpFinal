"""Resource engine monitors system load and evolves the ResourceNN for safe,
long-term operation."""

import importlib.util
try:
    import psutil
except Exception:  # pragma: no cover - psutil may be absent
    psutil = None
from pathlib import Path

torch = None
_torch_loaded = False


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
ResourceNN = load_module("imp_resource_nn", CORE_DIR / "imp-resource-nn.py").ResourceNN

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "imp-resource-log.json"

PINNED = []


def pin_memory(ram_mb=0, vram_mb=0):
    """Reserve RAM and optional VRAM by allocating blocks."""
    global torch, _torch_loaded
    if not _torch_loaded:
        try:
            import torch as _torch  # type: ignore
            torch = _torch
        except Exception:  # pragma: no cover - torch may be absent
            torch = None
        _torch_loaded = True
    block = {}
    if ram_mb > 0:
        block["ram"] = bytearray(int(ram_mb * 1024 * 1024))
    if vram_mb > 0 and torch and getattr(torch, "cuda", None) and torch.cuda.is_available():
        # allocate simple tensor on GPU
        size = int(vram_mb * 256)
        block["vram"] = torch.empty((size, 1024), device="cuda")
    PINNED.append(block)
    return block


def release_pins():
    """Release all pinned memory."""
    PINNED.clear()


def _pinned_usage():
    ram = sum(len(b.get("ram", b"")) for b in PINNED) / (1024 * 1024)
    vram = 0.0
    for b in PINNED:
        tensor = b.get("vram")
        if tensor is not None:
            vram += tensor.numel() * tensor.element_size() / (1024 * 1024)
    return ram, vram


def manage_resources():
    nn = neural_manager.get_or_create("resource", ResourceNN)
    if psutil:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory().percent
    else:
        cpu = mem = 0.0
    pin_ram, pin_vram = _pinned_usage()
    nn.evolve(cpu, mem, pin_ram, pin_vram)
    score = nn.predict(cpu, mem, pin_ram, pin_vram)
    record = {
        "cpu": cpu,
        "mem": mem,
        "pinned_ram": pin_ram,
        "pinned_vram": pin_vram,
        "score": score,
    }
    data = read_json(LOG_PATH, [])
    data.append(record)
    write_json(LOG_PATH, data)
    return record


if __name__ == "__main__":
    manage_resources()
