from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "self-improvement" / "imp-blockchain-ledger.py"
spec = importlib.util.spec_from_file_location("ledger", MODULE_PATH)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
LEDGER_FILE = ROOT / "logs" / "imp-blockchain-ledger.json"


def test_blockchain_ledger():
    print("Running Blockchain Ledger...")
    ledger.add_block()
    assert LEDGER_FILE.exists()
    data = ledger.load_ledger()[-1]
    sample_file = next(iter(data["files"].values()))
    assert "hash" in sample_file
    if "content" in sample_file:
        assert sample_file["content"].strip() != ""
    else:
        blob_path = sample_file.get("blob")
        assert blob_path, "Ledger entry missing blob reference"
        assert (ROOT / blob_path).exists(), "Ledger blob was not written"
    assert ledger.verify_chain(), "Blockchain verification failed"
    print("Blockchain Ledger Test Passed!")


test_blockchain_ledger()
