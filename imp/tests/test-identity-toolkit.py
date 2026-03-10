from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ISSUER = ROOT / "identity" / "issuer-service"
SDK = ROOT / "identity" / "sdk"


def test_issuer_service_scaffold():
    files = {
        "app.ts": "anchorConsentTyped",
        "did.ts": "verifyDIDJWS",
        "revocation.ts": "buildStatusBitmap",
        "util.ts": "nowSec",
        "tee.ts": "verifyTEEQuote",
        "chain.ts": "postStatusBitmap",
    }
    for name, marker in files.items():
        content = (ISSUER / name).read_text(encoding="utf-8")
        assert marker in content


def test_identity_sdk_scaffold():
    expected = {
        "wallet.ts": "createConsentReceipt",
        "verifier.ts": "verifyPresentation",
        "crypto.ts": "verifyJWS",
        "network.ts": "resolveIssuerPolicy",
        "bci-simulator.ts": "BCIIntentEnvelope",
        "bci-sim.ts": "makeBCIIntentEnvelope",
    }
    for name, marker in expected.items():
        text = (SDK / name).read_text(encoding="utf-8")
        assert marker in text

