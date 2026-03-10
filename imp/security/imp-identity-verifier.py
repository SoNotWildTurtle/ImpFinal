"""Utilities for verifying identity credentials against the companion registry.

This module focuses on client-side validation of verifiable credentials (VCs)
that reference Merkle roots published to the on-chain
``CompanionIdentityRegistry`` contract.  The helpers do not communicate with
the blockchain directly; instead they operate on data that has already been
fetched by another component (for example the processing manager or an
operator tool).

Key responsibilities:

* Verify Merkle proofs for credential revocation membership checks.
* Provide a high-level ``evaluate_credential`` helper that validates the
  structure of registry snapshots and returns a status summary.
* Offer lightweight utilities so other modules can record audit entries when
  a credential changes state.

The implementation intentionally sticks to Python's standard library so it can
run in constrained environments (offline nodes or recovery shells).  Hashing is
performed with ``sha256`` to match the default hashing strategy recommended in
the registry scaffold.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256, sha3_256
import json
from typing import Callable, Iterable, List, Mapping, MutableMapping, Optional, Sequence, MutableSet


class IdentityVerificationError(Exception):
    """Raised when a credential bundle is malformed or the proof fails."""


def _normalise_bytes(value: str) -> bytes:
    """Convert a hex string (with or without ``0x``) into bytes."""

    cleaned = value.lower().strip()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if len(cleaned) % 2:
        cleaned = f"0{cleaned}"
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise IdentityVerificationError(f"Invalid hex value: {value}") from exc


def _hash_pair(left: bytes, right: bytes) -> bytes:
    return sha256(left + right).digest()


def verify_merkle_membership(leaf: str, proof: Sequence[Mapping[str, str]], root: str) -> bool:
    """Verify that ``leaf`` is part of the Merkle tree with the supplied ``root``.

    The proof is expected to be an iterable of dictionaries with a ``hash`` key
    and an optional ``position`` key (``"left"`` or ``"right"``).  Missing
    positions default to ``"right"`` which matches the contract scaffold.
    """

    current = _normalise_bytes(leaf)
    for step in proof:
        sibling = _normalise_bytes(step["hash"])
        position = step.get("position", "right").lower()
        if position not in {"left", "right"}:
            raise IdentityVerificationError(f"Invalid proof position: {position}")
        if position == "left":
            current = _hash_pair(sibling, current)
        else:
            current = _hash_pair(current, sibling)

    expected_root = _normalise_bytes(root)
    return current == expected_root


def build_merkle_root(leaves: Iterable[str]) -> str:
    """Build a Merkle root from ``leaves`` (hex strings) using sha256 hashing.

    This helper is primarily used by the test-suite and offline auditors to
    craft synthetic revocation batches.  The implementation keeps the leaf
    ordering stable, inserting ``0x00`` siblings when a level has an odd number
    of nodes.
    """

    nodes = [_normalise_bytes(leaf) for leaf in leaves]
    if not nodes:
        return "0x" + sha256(b"").hexdigest()

    level = nodes
    while len(level) > 1:
        next_level: List[bytes] = []
        for idx in range(0, len(level), 2):
            left = level[idx]
            if idx + 1 < len(level):
                right = level[idx + 1]
            else:
                right = b"\x00"
            next_level.append(_hash_pair(left, right))
        level = next_level

    return "0x" + level[0].hex()


@dataclass
class CredentialStatus:
    credential_id: str
    issuer: str
    merkle_root: str
    revoked: bool
    proof_valid: bool
    detail: str


@dataclass
class ConsentAnchorStatus:
    ciphertext_hash: str
    matches: bool
    detail: str


@dataclass
class IntentValidationResult:
    session_id: str
    accepted: bool
    liveness_ok: bool
    freshness_ok: bool
    signature_ok: bool
    detail: str


@dataclass
class AttestationStatus:
    cmp_did: str
    ok: bool
    age_seconds: int
    detail: str


@dataclass
class StatusSnapshotResult:
    """Result of evaluating a status bitmap snapshot."""

    revoked: bool
    known: bool
    detail: str


@dataclass
class TypedConsentStatus:
    """Result of evaluating an EIP-712 typed consent anchor."""

    consent_hash: str
    digest: str
    accepted: bool
    detail: str


def build_status_bitmap(flags: Sequence[bool]) -> str:
    """Return a hex-encoded bitmap where set bits represent revoked entries."""

    if not flags:
        return "0x"

    byte_count = (len(flags) + 7) // 8
    data = bytearray(byte_count)
    for index, flagged in enumerate(flags):
        if flagged:
            byte_index = index // 8
            bit_index = index % 8
            data[byte_index] |= 1 << bit_index
    return "0x" + bytes(data).hex()


def _bitmap_bit_set(bitmap_hex: str, index: int) -> Optional[bool]:
    if bitmap_hex.lower() in {"0x", "0x0", ""}:
        return False

    data = _normalise_bytes(bitmap_hex)
    byte_index = index // 8
    bit_index = index % 8
    if byte_index >= len(data):
        return None
    return bool(data[byte_index] & (1 << bit_index))


def evaluate_status_snapshot(snapshot: Mapping[str, object], index: int) -> StatusSnapshotResult:
    """Evaluate a bitmap snapshot published alongside revocation Merkle roots."""

    bitset = snapshot.get("bitset")
    if not isinstance(bitset, str):
        raise IdentityVerificationError("Snapshot missing 'bitset' hex string")

    declared_length = int(snapshot.get("length", 0))
    revoked = _bitmap_bit_set(bitset, index)
    if revoked is None:
        return StatusSnapshotResult(revoked=False, known=False, detail="Index outside bitmap range")

    if declared_length and index >= declared_length:
        return StatusSnapshotResult(revoked=False, known=False, detail="Index beyond declared length")

    detail = "Credential marked revoked in bitmap" if revoked else "Credential not present in bitmap"
    return StatusSnapshotResult(revoked=bool(revoked), known=True, detail=detail)


def evaluate_credential(bundle: Mapping[str, object]) -> CredentialStatus:
    """Evaluate a credential bundle returned by the issuer microservice.

    ``bundle`` must contain ``credential_id``, ``issuer``, ``revocation_root``
    and a ``proof`` list.  If the proof validates against the supplied root the
    credential is considered revoked (membership proof).  Callers can represent
    non-revocation by omitting the proof or passing an empty list.
    """

    required = {"credential_id", "issuer", "revocation_root"}
    missing = required.difference(bundle)
    if missing:
        raise IdentityVerificationError(f"Missing fields: {sorted(missing)}")

    credential_id = str(bundle["credential_id"])
    issuer = str(bundle["issuer"])
    root = str(bundle["revocation_root"])
    proof = bundle.get("proof") or []

    if not isinstance(proof, Sequence):
        raise IdentityVerificationError("Proof must be a sequence of steps")

    if not proof:
        return CredentialStatus(
            credential_id=credential_id,
            issuer=issuer,
            merkle_root=root,
            revoked=False,
            proof_valid=False,
            detail="No membership proof provided; treating as not revoked",
        )

    proof_valid = verify_merkle_membership(credential_id, proof, root)
    if proof_valid:
        detail = "Credential ID is present in revocation set"
    else:
        detail = "Merkle proof did not match provided root"

    return CredentialStatus(
        credential_id=credential_id,
        issuer=issuer,
        merkle_root=root,
        revoked=proof_valid,
        proof_valid=proof_valid,
        detail=detail,
    )


def hash_consent_receipt(ciphertext: object) -> str:
    """Return a ``sha256`` hash for the encrypted consent receipt."""

    if isinstance(ciphertext, bytes):
        data = ciphertext
    else:
        data = str(ciphertext).encode("utf-8")
    return "0x" + sha256(data).hexdigest()


def verify_consent_anchor(ciphertext: object, anchored_hash: str) -> ConsentAnchorStatus:
    """Compare the ciphertext hash against the on-chain anchor."""

    calculated = hash_consent_receipt(ciphertext)
    matches = calculated.lower() == anchored_hash.lower()
    detail = "Anchor matches encrypted receipt" if matches else "Anchor mismatch"
    return ConsentAnchorStatus(ciphertext_hash=calculated, matches=matches, detail=detail)


def _domain_to_bytes(domain_separator: str | bytes) -> bytes:
    if isinstance(domain_separator, bytes):
        return domain_separator
    cleaned = domain_separator.strip()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if not cleaned:
        raise IdentityVerificationError("Domain separator cannot be empty")
    if len(cleaned) % 2:
        cleaned = f"0{cleaned}"
    return bytes.fromhex(cleaned)


def compute_typed_consent_digest(
    domain_separator: str | bytes,
    consent_hash: str,
    issued_at: int,
    nonce: int,
) -> bytes:
    """Compute an EIP-712 style digest for the consent struct."""

    type_hash = sha3_256(b"Consent(bytes32 consentHash,uint256 issuedAt,uint256 nonce)").digest()
    consent_bytes = _normalise_bytes(consent_hash)
    issued_bytes = issued_at.to_bytes(32, "big")
    nonce_bytes = nonce.to_bytes(32, "big")
    struct_hash = sha3_256(type_hash + consent_bytes + issued_bytes + nonce_bytes).digest()
    domain_bytes = _domain_to_bytes(domain_separator)
    return sha3_256(b"\x19\x01" + domain_bytes + struct_hash).digest()


def verify_typed_consent_anchor(
    *,
    domain_separator: str | bytes,
    consent_hash: str,
    issued_at: int,
    nonce: int,
    signature: Mapping[str, object],
    seen_digests: Optional[MutableSet[bytes]] = None,
    signature_verifier: Optional[Callable[[bytes, Mapping[str, object]], bool]] = None,
) -> TypedConsentStatus:
    """Validate a typed consent anchor and guard against replay attacks."""

    digest = compute_typed_consent_digest(domain_separator, consent_hash, issued_at, nonce)
    if seen_digests is not None and digest in seen_digests:
        return TypedConsentStatus(
            consent_hash=consent_hash,
            digest="0x" + digest.hex(),
            accepted=False,
            detail="Replay detected for consent digest",
        )

    verifier = signature_verifier or (lambda message, sig: bool(sig.get("sig")))
    signature_ok = verifier(digest, signature)
    detail = "Typed consent accepted" if signature_ok else "Typed consent signature rejected"

    if signature_ok and seen_digests is not None:
        seen_digests.add(digest)

    return TypedConsentStatus(
        consent_hash=consent_hash,
        digest="0x" + digest.hex(),
        accepted=signature_ok,
        detail=detail,
    )


def validate_intent_envelope(
    envelope: MutableMapping[str, object],
    *,
    min_liveness: float = 0.95,
    max_freshness_ms: int = 2_000,
    signature_verifier: Optional[Callable[[bytes, Mapping[str, object]], bool]] = None,
) -> IntentValidationResult:
    """Validate a signed BCI intent envelope before acting on it."""

    required_top = {"bci_did", "user_did", "session_id", "timestamp", "intent", "liveness", "proof"}
    missing = required_top.difference(envelope)
    if missing:
        raise IdentityVerificationError(f"Missing envelope fields: {sorted(missing)}")

    intent = envelope["intent"]
    if not isinstance(intent, Mapping):
        raise IdentityVerificationError("Intent must be a mapping")
    for key in ("class", "action"):
        if key not in intent:
            raise IdentityVerificationError(f"Intent missing field: {key}")

    liveness = envelope["liveness"]
    if not isinstance(liveness, Mapping):
        raise IdentityVerificationError("Liveness block must be a mapping")

    score = float(liveness.get("score", 0.0))
    freshness = int(liveness.get("freshness_ms", 0))
    liveness_ok = score >= min_liveness
    freshness_ok = freshness <= max_freshness_ms

    proof = envelope["proof"]
    if not isinstance(proof, Mapping):
        raise IdentityVerificationError("Proof block must be a mapping")

    payload = envelope.copy()
    payload.pop("proof", None)
    signature_ok: bool
    if signature_verifier:
        signature_ok = signature_verifier(_canonical_json(payload), proof)
    else:
        signature_ok = bool(proof.get("sig"))

    accepted = liveness_ok and freshness_ok and signature_ok
    detail_parts = []
    if not liveness_ok:
        detail_parts.append("Liveness score below threshold")
    if not freshness_ok:
        detail_parts.append("Intent envelope is stale")
    if not signature_ok:
        detail_parts.append("Signature verification failed")
    if not detail_parts:
        detail_parts.append("Envelope accepted")

    return IntentValidationResult(
        session_id=str(envelope["session_id"]),
        accepted=accepted,
        liveness_ok=liveness_ok,
        freshness_ok=freshness_ok,
        signature_ok=signature_ok,
        detail="; ".join(detail_parts),
    )


def evaluate_attestation_report(
    report: Mapping[str, object],
    *,
    expected_model_hash: str,
    expected_config_hash: Optional[str] = None,
    max_age_seconds: int = 2_592_000,
) -> AttestationStatus:
    """Validate companion attestation metadata returned by the issuer service."""

    required = {"cmp_did", "reportDigest", "runtimeVersion", "attestedAt", "model_hash"}
    missing = required.difference(report)
    if missing:
        raise IdentityVerificationError(f"Missing attestation fields: {sorted(missing)}")

    cmp_did = str(report["cmp_did"])
    model_hash = str(report["model_hash"]).lower()
    config_hash = str(report.get("config_hash", "")).lower()

    if model_hash != expected_model_hash.lower():
        return AttestationStatus(
            cmp_did=cmp_did,
            ok=False,
            age_seconds=0,
            detail="Model hash mismatch",
        )

    if expected_config_hash and config_hash and config_hash != expected_config_hash.lower():
        return AttestationStatus(
            cmp_did=cmp_did,
            ok=False,
            age_seconds=0,
            detail="Configuration hash mismatch",
        )

    attested_at = _iso_to_datetime(str(report["attestedAt"]))
    age_seconds = int((datetime.now(timezone.utc) - attested_at).total_seconds())

    if age_seconds > max_age_seconds:
        return AttestationStatus(
            cmp_did=cmp_did,
            ok=False,
            age_seconds=age_seconds,
            detail="Attestation is older than policy allows",
        )

    return AttestationStatus(
        cmp_did=cmp_did,
        ok=True,
        age_seconds=age_seconds,
        detail="Attestation accepted",
    )


__all__ = [
    "CredentialStatus",
    "IdentityVerificationError",
    "build_merkle_root",
    "build_status_bitmap",
    "StatusSnapshotResult",
    "evaluate_status_snapshot",
    "evaluate_credential",
    "evaluate_attestation_report",
    "hash_consent_receipt",
    "IntentValidationResult",
    "AttestationStatus",
    "ConsentAnchorStatus",
    "TypedConsentStatus",
    "compute_typed_consent_digest",
    "verify_consent_anchor",
    "verify_typed_consent_anchor",
    "validate_intent_envelope",
    "verify_merkle_membership",
]

def _iso_to_datetime(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalise it to UTC."""

    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned).astimezone(timezone.utc)


def _canonical_json(payload: Mapping[str, object]) -> bytes:
    """Return a canonical JSON representation suitable for hashing/signing."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

