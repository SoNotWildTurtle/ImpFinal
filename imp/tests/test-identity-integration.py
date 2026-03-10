from pathlib import Path
import importlib.util
from datetime import datetime, timedelta, timezone
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "security" / "imp-identity-verifier.py"

spec = importlib.util.spec_from_file_location("identity_verifier_integration", MODULE)
identity = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = identity
spec.loader.exec_module(identity)

print("Running Identity Integration Scenarios...")

leaves = ["0xaaa0", "0xbbb1", "0xccc2", "0xddd3"]
root_hash = identity.build_merkle_root(leaves)
leaf = leaves[1]
proof = [
    {"hash": "0xaaa0", "position": "left"},
    {"hash": identity.build_merkle_root(leaves[2:]), "position": "right"},
]
status = identity.evaluate_credential(
    {
        "credential_id": leaf,
        "issuer": "did:example:issuer",
        "revocation_root": root_hash,
        "proof": proof,
    }
)
assert status.revoked is True

bitmap = identity.build_status_bitmap([False, True, False, False])
bitmap_status = identity.evaluate_status_snapshot({"bitset": bitmap, "length": 4}, 1)
assert bitmap_status.revoked is True and bitmap_status.known is True

unknown_bitmap = identity.evaluate_status_snapshot({"bitset": bitmap, "length": 2}, 3)
assert unknown_bitmap.known is False

ciphertext = b"encrypted consent"
anchored_hash = identity.hash_consent_receipt(ciphertext)
anchor_status = identity.verify_consent_anchor(ciphertext, anchored_hash)
assert anchor_status.matches is True

domain_separator = "0x" + "11" * 32
seen_digests = set()
consent_status = identity.verify_typed_consent_anchor(
    domain_separator=domain_separator,
    consent_hash=anchored_hash,
    issued_at=1700000000,
    nonce=1,
    signature={"sig": "ok"},
    seen_digests=seen_digests,
    signature_verifier=lambda digest, sig: sig.get("sig") == "ok",
)
assert consent_status.accepted is True

replay = identity.verify_typed_consent_anchor(
    domain_separator=domain_separator,
    consent_hash=anchored_hash,
    issued_at=1700000000,
    nonce=1,
    signature={"sig": "ok"},
    seen_digests=seen_digests,
)
assert replay.accepted is False

envelope = {
    "bci_did": "did:bci:abc",
    "user_did": "did:usr:xyz",
    "session_id": "urn:uuid:123",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "intent": {
        "class": "CONSENT",
        "action": "bind_companion",
        "params": {"scope": ["identity.bind"]},
    },
    "liveness": {"method": "local-biometric", "score": 0.99, "freshness_ms": 500},
    "proof": {"alg": "Ed25519", "sig": "stub"},
}
intent_status = identity.validate_intent_envelope(envelope.copy())
assert intent_status.accepted is True

stale = envelope.copy()
stale["liveness"] = {"method": "local-biometric", "score": 0.6, "freshness_ms": 9_000}
stale_result = identity.validate_intent_envelope(stale)
assert stale_result.accepted is False

attestation = {
    "cmp_did": "did:cmp:123",
    "model_hash": "sha256:model",
    "config_hash": "sha256:cfg",
    "reportDigest": "sha256:xyz",
    "runtimeVersion": "cmp/1.2.3",
    "attestedAt": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
}
att_status = identity.evaluate_attestation_report(
    attestation,
    expected_model_hash="sha256:model",
    expected_config_hash="sha256:cfg",
    max_age_seconds=600,
)
assert att_status.ok is True

expired_attestation = dict(attestation)
expired_attestation["attestedAt"] = (
    datetime.now(timezone.utc) - timedelta(days=40)
).isoformat()
expired = identity.evaluate_attestation_report(
    expired_attestation,
    expected_model_hash="sha256:model",
    expected_config_hash="sha256:cfg",
    max_age_seconds=600,
)
assert expired.ok is False

latest_root = identity.build_merkle_root(["0xaaa0", "0xbbb1"])
old_status = identity.evaluate_credential(
    {
        "credential_id": "0xccc2",
        "issuer": "did:example:issuer",
        "revocation_root": latest_root,
        "proof": [],
    }
)
assert old_status.revoked is False

print("Identity Integration Scenarios Passed")
