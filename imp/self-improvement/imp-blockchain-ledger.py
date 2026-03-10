import json
import hashlib
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER_FILE = ROOT / "logs" / "imp-blockchain-ledger.json"
BLOB_DIR = ROOT / "logs" / "imp-ledger-blobs"
MAX_BLOCKS = 5
CODE_DIR = ROOT


def snapshot_code() -> dict:
    """Return a mapping of file paths to their hash and decoded content."""

    files = [
        p
        for p in CODE_DIR.glob("**/*.py")
        if "__pycache__" not in str(p) and BLOB_DIR not in p.parents
    ]
    result = {}
    for path in files:
        try:
            content = path.read_bytes()
            result[str(path.relative_to(ROOT))] = {
                "hash": hashlib.sha256(content).hexdigest(),
                "content": content.decode("utf-8", errors="ignore"),
            }
        except Exception:
            # Ignore unreadable files but continue building the snapshot.
            pass
    return result


def _write_blob(block_hash: str, rel_path: str, content: str) -> str:
    """Persist file content for a block and return the relative blob path."""

    BLOB_DIR.mkdir(parents=True, exist_ok=True)
    blob_root = BLOB_DIR / block_hash
    target = blob_root / Path(rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target.relative_to(ROOT))


def load_ledger() -> list:
    if not LEDGER_FILE.exists():
        return []

    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        entries = json.load(f)

    changed = False
    blob_parts = BLOB_DIR.relative_to(ROOT).parts
    for entry in entries:
        block_hash = entry.get("block_hash", "legacy")
        files = entry.get("files", {})
        for rel_path, info in files.items():
            if not isinstance(info, dict):
                continue
            rel_parts = Path(rel_path).parts
            if blob_parts and rel_parts[:len(blob_parts)] == blob_parts:
                if "content" in info:
                    info.pop("content", None)
                    changed = True
                continue
            if "content" in info:
                blob_path = info.get("blob")
                if not blob_path:
                    blob_path = _write_blob(block_hash, rel_path, info["content"])
                    info["blob"] = blob_path
                info.pop("content", None)
                changed = True
    if changed:
        save_ledger(entries)
    return entries


def save_ledger(entries: list) -> None:
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, separators=(",", ":"))
        f.write("\n")


def add_block() -> dict:
    ledger = load_ledger()
    prev_hash = ledger[-1]["block_hash"] if ledger else ""
    files = snapshot_code()
    # use only hashes when computing block hash so content doesn't affect verification
    hash_map = {p: info["hash"] for p, info in files.items()}
    block_data = json.dumps({"prev_hash": prev_hash, "files": hash_map}, sort_keys=True)
    block_hash = hashlib.sha256(block_data.encode()).hexdigest()
    entry_files = {}
    for rel_path, info in files.items():
        entry_info = {"hash": info["hash"]}
        content = info.get("content")
        if content is not None:
            try:
                entry_info["blob"] = _write_blob(block_hash, rel_path, content)
            except Exception:
                # Fall back to inline content if writing fails so recovery still works.
                entry_info["content"] = content
        entry_files[rel_path] = entry_info
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "prev_hash": prev_hash,
        "block_hash": block_hash,
        "files": entry_files,
    }
    ledger.append(entry)
    if len(ledger) > MAX_BLOCKS:
        ledger = ledger[-MAX_BLOCKS:]
    save_ledger(ledger)
    return entry


def verify_chain() -> bool:
    ledger = load_ledger()
    if not ledger:
        return True
    prev_hash = ledger[0].get("prev_hash", "")
    for entry in ledger:
        hash_map = {}
        for p, info in entry["files"].items():
            if isinstance(info, dict):
                hash_map[p] = info.get("hash", "")
            else:
                hash_map[p] = info
        data = json.dumps({"prev_hash": prev_hash, "files": hash_map}, sort_keys=True)
        if hashlib.sha256(data.encode()).hexdigest() != entry["block_hash"]:
            return False
        prev_hash = entry["block_hash"]
    return True


if __name__ == "__main__":
    add_block()
    print("Ledger valid:", verify_chain())
