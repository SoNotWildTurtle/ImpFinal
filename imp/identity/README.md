# IMP Identity Verification Toolkit

This directory contains building blocks for the consent-first identity
verification workflow referenced in the latest roadmap notes.  The goal is to
provide a clear hand-off between the on-chain registry, the issuer
microservice, and local wallet flows so IMP can reason about trusted operators
in both online and offline deployments.

## Components

* `CompanionIdentityRegistry.sol` – Minimal registry scaffold for trusted
  issuers, revocation batches and basic consent anchoring.
* `CompanionIdentityRegistryV2.sol` – Expanded registry with issuer/auditor
  roles, status bitmap snapshots, typed consent anchoring and a pause switch for
  emergency response.  Deploy on an EVM-compatible chain (L2 recommended) and
  keep gas costs low by posting Merkle roots or compact bitmaps rather than raw
  lists.
* `issuer-service/app.ts` – Fastify/TypeScript skeleton that verifies typed
  consent JWS payloads, checks TEE attestations, issues verifiable credentials,
  publishes revocation snapshots, and anchors consent hashes on-chain.
* `issuer-service/did.ts` – Helpers for verifying DID-signed consent receipts
  and generating stub signatures for the demo flows.
* `issuer-service/revocation.ts` – In-memory revocation state, Merkle root
  builder, and compact status-bitmap generator used by the demo microservice.
* `issuer-service/util.ts` – Shared hashing utilities for posting roots and
  status snapshots.
* `issuer-service/chain.ts` – Stubs for interacting with the registry contract
  via Ethers.js; in production replace the console logging with real contract
  calls.
* `issuer-service/tee.ts` – Attestation verifier facade that can be swapped for
  Intel DCAP, AMD SEV-SNP, or TPM backends.
* `identity/sdk/` – Wallet, verifier, crypto, network, and BCI simulator
  scaffolds illustrating selective disclosure, consent receipt creation, and
  intent envelope flows for integration testing.
* `identity/sdk/bci-sim.ts` – Minimal helper for constructing signed intent
  envelopes with configurable DIDs and scopes, demonstrating how live BCI
  gateways can feed data into the issuer workflow.
* `wallet/notes.md` – Quick reference for wallet responsibilities when
  presenting CompanionBindingCredential proofs to verifiers.
* `BCI_COMPANION_SPEC.md` – Working draft of the BCI companion attestation
  profile, intent envelopes, and verification checklist used by the identity
  pipeline.

## Usage

1. Deploy the registry contract and register your issuer address with
   `setIssuer`.
2. Run the issuer microservice, configure it with chain credentials and publish
   its DID document.
3. Wallets consume the issued credentials and submit Merkle proofs derived from
   `postRevocationRoot` batches when interacting with verifiers.

Client-side Python helpers live in `imp/security/imp-identity-verifier.py` and
are exercised by the automated test suite to guarantee Merkle proofs are
validated consistently.  The helpers now also expose consent-receipt hashing,
status bitmap inspection, typed consent digest verification, intent-envelope
validation, and companion attestation checks so wallet flows can anchor
receipts, confirm runtime integrity, and guard against replay attacks before
escalating trust.

## Integration & Test Plan

`imp/tests/test-identity-integration.py` walks through the end-to-end scenarios
outlined in the BCI companion spec:

1. **Happy path** – bind a companion using a consent envelope, validate the TEE
   quote, and confirm the credential is absent from both Merkle and bitmap
   revocation data.
2. **Presentation & verify** – construct a selective-disclosure style bundle
   and ensure the verifier-side helpers approve both the proof and the consent
   anchor.
3. **Revocation & migration** – rotate issuer material, publish a new Merkle
   root, and confirm the previous credential is rejected.
4. **Negative cases** – stale intent envelopes, replayed consent digests, and
   outdated attestations are all exercised to keep regression coverage tight.

Additional fixtures under `imp/identity/BCI_COMPANION_SPEC.md` document gas
benchmarks, recovery drills, and privacy expectations so future iterations of
the issuer microservice and wallet flows stay aligned with the roadmap.

The new SDK directory also contains TypeScript stubs for wallet and verifier
testing, plus a BCI intent-envelope simulator so operators can validate human
consent, liveness, and selective-disclosure behaviour before wiring in full
cryptographic libraries.  The `bci-sim.ts` helper now mirrors the consent
envelope flow described in the roadmap and is ready for integration with more
advanced signing backends.

## ZK / Selective Disclosure Drop-ins

The wallet and verifier scaffolds intentionally expose clear seams for
zero-knowledge upgrades:

* **Selective disclosure** – Replace the internals of `wallet.presentVP()` with
  a BBS+ or SNARK-based proof so verifiers learn only the requested attributes
  (for example “holds a valid CompanionBindingCredential”).
* **Predicate checks** – Add a Noir or Circom circuit that proves predicates
  such as `age ≥ 18` while keeping birth dates private.  The verifier stub in
  `sdk/verifier.ts` is ready to accept additional proof objects before granting
  access.

These notes give operators a concrete starting point for migrating the demo
flows toward production-grade privacy guarantees.

