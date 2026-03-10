# Wallet responsibilities

* Safely store the CompanionBindingCredential issued by the microservice.
* Supply Merkle proofs for revocation checks – proofs can be fetched from the
  issuer API or generated locally from batched snapshots.
* Support selective disclosure (e.g. BBS+, zk proofs) so only the required
  predicates are shared during verifier presentations.
* Maintain recovery material (passkeys, guardian shares) so the user can regain
  access if the device is lost.
* Attach proof-of-non-revocation data in every presentation and surface the
  consent receipt hash for operator transparency.

