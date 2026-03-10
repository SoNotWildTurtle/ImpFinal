from pathlib import Path
import importlib.util
import json
from datetime import datetime, timedelta, timezone
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'security' / 'imp-identity-verifier.py'

spec = importlib.util.spec_from_file_location('identity_verifier', MODULE)
identity = importlib.util.module_from_spec(spec)
sys.modules['identity_verifier'] = identity
spec.loader.exec_module(identity)

print('Testing Identity Verifier...')

LEAVES = ['0xaaa0', '0xbbb1', '0xccc2', '0xddd3']
ROOT_HASH = identity.build_merkle_root(LEAVES)

leaf = LEAVES[2]

# Build proof manually using helper to ensure coverage of API contract.
proof = [
    {'hash': '0xddd3', 'position': 'right'},
    {'hash': identity.build_merkle_root(LEAVES[:2])[2:], 'position': 'left'},
]

assert identity.verify_merkle_membership(leaf, proof, ROOT_HASH)

status = identity.evaluate_credential({
    'credential_id': leaf,
    'issuer': 'did:example:issuer',
    'revocation_root': ROOT_HASH,
    'proof': proof,
})

assert status.revoked is True
assert status.proof_valid is True

not_revoked = identity.evaluate_credential({
    'credential_id': '0xffff',
    'issuer': 'did:example:issuer',
    'revocation_root': ROOT_HASH,
    'proof': [],
})

assert not_revoked.revoked is False
assert not_revoked.proof_valid is False

ciphertext = json.dumps({"consent": "granted"}).encode()
anchored = identity.hash_consent_receipt(ciphertext)
anchor_status = identity.verify_consent_anchor(ciphertext, anchored)
assert anchor_status.matches is True

envelope = {
    "bci_did": "did:bci:abc",
    "user_did": "did:usr:xyz",
    "session_id": "urn:uuid:123",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "intent": {"class": "CONSENT", "action": "bind_companion", "params": {"scope": ["identity.bind"]}},
    "liveness": {"method": "local-biometric", "score": 0.99, "freshness_ms": 500},
    "proof": {"alg": "Ed25519", "sig": "stub"},
}

intent_status = identity.validate_intent_envelope(envelope.copy())
assert intent_status.accepted is True
assert intent_status.signature_ok is True

attestation = {
    "cmp_did": "did:cmp:123",
    "model_hash": "sha256:abcd",
    "config_hash": "sha256:cfg",
    "reportDigest": "sha256:xyz",
    "runtimeVersion": "cmp/1.2.3",
    "attestedAt": (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat(),
}

att_status = identity.evaluate_attestation_report(
    attestation,
    expected_model_hash="sha256:abcd",
    expected_config_hash="sha256:cfg",
    max_age_seconds=3600,
)
assert att_status.ok is True

