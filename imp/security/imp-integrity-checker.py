import hashlib
import importlib.util
from pathlib import Path


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
imp_utils = load_module("imp_utils", ROOT / "core" / "imp_utils.py")
write_json = imp_utils.write_json

INTEGRITY_LOG = ROOT / "logs" / "imp-integrity-log.json"
WATCHED_FILES = [
    Path("/etc/passwd"),
    Path("/etc/shadow"),
    Path("/etc/ssh/sshd_config"),
    Path("/etc/sudoers"),
]


def calculate_file_hash(file_path: Path):
    if not file_path.exists():
        return None
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def check_integrity():
    integrity_status = {}
    for file in WATCHED_FILES:
        file_hash = calculate_file_hash(file)
        if file_hash:
            integrity_status[str(file)] = file_hash
    write_json(INTEGRITY_LOG, integrity_status)


if __name__ == "__main__":
    check_integrity()
