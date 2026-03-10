# BCI Companion Attestation Spec (v0.1)

This note captures the practical requirements discussed for binding a brain–computer
interface (BCI) companion to an operator using the IMP identity pipeline. It is
kept lightweight so the microservice and wallet scaffolds can evolve without a
full rewrite.

## Entities and Keys

- **User Wallet (`did:usr:*`)** – Approves consent requests, stores credentials,
  and produces verifiable presentations.
- **BCI Gateway (`did:bci:*`)** – Runs on user-controlled hardware, performs
  liveness checks, and signs intent envelopes with a hardware-protected key.
- **Companion Agent (`did:cmp:*`)** – Runs in a TEE/HSM backed environment,
  serves attestation responses, and honours anchored consent receipts.

## Measurements in Attestation Quotes

Quotes produced by TPM, SGX, SEV or similar roots of trust must include:

- Secure boot / firmware digest (e.g., PCR0)
- OS kernel or hypervisor hash
- Companion runtime binary digest
- Model or weights bundle digest
- Policy / configuration digest (allow lists, ACLs)
- Verifier-provided nonce to prevent replay attacks
- Optional blinded device serial for accountability without leaking PII

## Intent Envelope (BCI → Companion)

BCI gateways never stream raw EEG or biometric data. Instead they issue signed
intent envelopes. A minimal envelope looks like:

```json
{
  "type": "BCIIntentEnvelope",
  "bci_did": "did:bci:abc",
  "user_did": "did:usr:xyz",
  "session_id": "urn:uuid:...",
  "timestamp": "2025-10-10T12:34:56Z",
  "intent": {
    "class": "CONSENT",
    "action": "bind_companion",
    "params": { "companion_did": "did:cmp:123", "scope": ["identity.bind"] }
  },
  "liveness": {
    "method": "local-biometric",
    "score": 0.997,
    "freshness_ms": 820
  },
  "proof": {
    "alg": "Ed25519",
    "sig": "base64..."
  }
}
```

Gateways must ensure liveness exceeds the configured threshold and that
freshness is within a few seconds of the request.

## Companion Attestation Endpoint

Agents expose `POST /attest` that accepts the device DID, nonce, vendor quote,
model hash and configuration hash. Responses must include the canonical runtime
version, digest, and timestamp. Verifiers reject quotes older than policy
allows (e.g., 30 days) or whose hashes do not match a trusted allow list.

## Consent Policy

For identity binding, permission escalation, or data export:

1. BCI gateway issues an intent envelope that satisfies liveness/freshness.
2. User wallet displays a human-readable consent description and signs a
   consent receipt.
3. The receipt is encrypted (user key or guardian shared secret).
4. The issuer or wallet anchors `sha256(ciphertext)` on-chain via
   `anchorConsent` in `CompanionIdentityRegistry`.

The encrypted receipts remain off-chain; only hashes/roots are posted. Anchors
are append-only and provide a tamper-evident audit trail.

## Verification Checklist

- Crypto primitives: key generation, DID document parsing, JWS/JWT verification,
  and sanity checks for BBS+/ZK proofs.
- Attestation parsing: TPM/TEE quote validation, chain of trust verification,
  nonce freshness, and hash comparisons.
- Solidity contract: allowlist toggles, Merkle root posting, and event
  correctness for `CompanionIdentityRegistry`.
- Wallet UX: ensure consent UIs are human-readable and receipts are encrypted
  before anchoring.

## Integration Tests

1. **Happy path (bind)** – user creates a DID, the BCI gateway issues a consent
   envelope, the issuer verifies the envelope and attestation, issues a
   CompanionBindingCredential, and anchors the consent hash.
2. **Presentation & verify** – wallet produces a selective-disclosure VP showing
   `age ≥ 18` and the binding relationship.  Verifier checks issuer keys and the
   latest revocation proof.
3. **Revocation** – issuer posts a new revocation Merkle root; verifiers reject
   the old credential when presented with the fresh proof.
4. **Migration** – operator spins up a new companion, re-attests, re-issues the
   VC, and verifies the previous binding is invalidated in the audit trail.
5. **Key rotation** – issuer rotates its signing key, updates the DID document,
   and ensures historical signatures remain valid while new credentials use the
   rotated key.

## Adversarial / Negative Scenarios

- **Replay attacks** – detect stale attestation quotes by checking the embedded
  nonce and rejecting reused payloads.
- **Stolen BCI device** – require wallet co-consent; intent envelopes without
  wallet approval fail.
- **Compromised issuer** – remove an issuer from the allowlist and ensure newly
  issued VCs are rejected immediately.
- **Correlation leakage** – enforce pairwise DIDs and minimal VP disclosures so
  logs cannot correlate users across verifiers.

## Performance & Cost Notes

- Benchmark gas for posting revocation roots and consent anchors on the chosen
  L2; prefer batched updates.
- Simulate 10k credential revocations to estimate Merkle depth, bitmap size, and
  proof latency for wallet/verifier flows.
- Measure cold-start attestation times (SGX/SEV) and set verifier timeouts
  accordingly.

## Recovery & Guardianship Drills

- **Lost wallet** – exercise 3-of-5 guardian recovery, re-issue the binding VC,
  and confirm the consent anchor shows the recovery trail.
- **Time-lock / incapacity** – model escrow policies using a notarised policy VC
  and ensure audits reflect the release.

## Privacy & Compliance Checks

- Regularly scan on-chain data to guarantee only hashes/roots are posted.
- Exercise the right-to-revoke workflow: user triggers revocation, issuer posts
  the updated root within SLA, and verifiers honour the change.
- Validate data-retention policies so encrypted consent receipts are purged on
  schedule while their anchors remain immutable.

## Getting Started Checklist

1. Deploy the registry (v1 or v2) to an L2 testnet and register the issuer.
2. Implement the issuer microservice stubs (`postRevocationRoot`,
   `anchorConsentTyped`).
3. Build a wallet prototype that can generate a DID, store issued VCs, produce a
   VP with a revocation proof, and render a consent receipt before anchoring the
   ciphertext hash.
4. Create a BCI gateway simulator that emits signed intent envelopes with mock
   liveness so end-to-end tests can run locally (see
   `identity/sdk/bci-simulator.ts` for the full demo and `identity/sdk/bci-sim.ts`
   for a lightweight helper that mirrors production gateways).

For privacy upgrades, swap the wallet presentation routine with BBS+ or SNARK
proofs so verifiers learn only the requested predicates (for example `age ≥ 18`).
`identity/README.md` outlines the recommended drop-in points.

This checklist feeds into IMP's self-analysis so regressions or missing
coverage can be surfaced as roadmap goals.
