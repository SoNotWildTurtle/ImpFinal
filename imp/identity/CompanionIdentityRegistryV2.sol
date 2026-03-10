// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
 * Companion Identity Registry v2
 * - Issuer allowlist + roles
 * - Revocation: Merkle roots + status bitmaps
 * - EIP-712 typed consent anchors
 * - Pause switch for emergencies
 *
 * NOTE: Store only hashes/roots; never PII.
 */
contract CompanionIdentityRegistryV2 {
    // --- ownership / pause ---
    address public owner;
    bool    public paused;

    modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }
    modifier whenNotPaused() { require(!paused, "paused"); _; }

    // --- roles ---
    mapping(address => bool) public isIssuer;
    mapping(address => bool) public isAuditor;

    event OwnerChanged(address indexed newOwner);
    event Paused(bool on);
    event IssuerSet(address indexed issuer, bool allowed);
    event AuditorSet(address indexed auditor, bool allowed);

    // --- revocation (Merkle roots) ---
    struct RevocationBatch { bytes32 merkleRoot; uint256 timestamp; }
    mapping(address => RevocationBatch[]) public revocationBatches; // issuer => batches
    event RevocationRootPosted(address indexed issuer, bytes32 merkleRoot, uint256 index);

    // --- status bitmap (compact, append-only snapshots) ---
    struct StatusBitmap { bytes32 contentHash; uint256 length; uint256 timestamp; }
    mapping(address => StatusBitmap[]) public statusBitmaps; // issuer => snapshots
    event StatusBitmapPosted(address indexed issuer, bytes32 contentHash, uint256 length, uint256 index);

    // --- EIP-712 consent anchor ---
    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant CONSENT_TYPEHASH = keccak256(
        "Consent(bytes32 consentHash,uint256 issuedAt,uint256 nonce)"
    );
    mapping(bytes32 => bool) public consentSeen; // replay guard by (hash of struct)
    event ConsentAnchored(bytes32 indexed consentHash, address indexed submitter, uint256 issuedAt, uint256 nonce);

    constructor() {
        owner = msg.sender;
        uint256 chainId; assembly { chainId := chainid() }
        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes("CompanionIdentityRegistry")),
            keccak256(bytes("2")),
            chainId,
            address(this)
        ));
    }

    // --- admin ---
    function setOwner(address newOwner) external onlyOwner {
        owner = newOwner; emit OwnerChanged(newOwner);
    }
    function setPaused(bool on) external onlyOwner { paused = on; emit Paused(on); }
    function setIssuer(address who, bool allowed) external onlyOwner {
        isIssuer[who] = allowed; emit IssuerSet(who, allowed);
    }
    function setAuditor(address who, bool allowed) external onlyOwner {
        isAuditor[who] = allowed; emit AuditorSet(who, allowed);
    }

    // --- issuer ops ---
    function postRevocationRoot(bytes32 merkleRoot) external whenNotPaused {
        require(isIssuer[msg.sender], "issuer only");
        revocationBatches[msg.sender].push(RevocationBatch({
            merkleRoot: merkleRoot, timestamp: block.timestamp
        }));
        emit RevocationRootPosted(msg.sender, merkleRoot, revocationBatches[msg.sender].length - 1);
    }

    /// @notice Post a content-addressed status bitmap snapshot (e.g., keccak of the raw bitset)
    function postStatusBitmap(bytes32 contentHash, uint256 length) external whenNotPaused {
        require(isIssuer[msg.sender], "issuer only");
        statusBitmaps[msg.sender].push(StatusBitmap({
            contentHash: contentHash, length: length, timestamp: block.timestamp
        }));
        emit StatusBitmapPosted(msg.sender, contentHash, length, statusBitmaps[msg.sender].length - 1);
    }

    /// @notice EIP-712 typed consent anchoring; the signer is the submitter (wallet or companion)
    function anchorConsentTyped(
        bytes32 consentHash,
        uint256 issuedAt,
        uint256 nonce,
        uint8 v, bytes32 r, bytes32 s
    ) external whenNotPaused {
        bytes32 structHash = keccak256(abi.encode(CONSENT_TYPEHASH, consentHash, issuedAt, nonce));
        require(!consentSeen[structHash], "replay");
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", DOMAIN_SEPARATOR, structHash));

        address signer = ecrecover(digest, v, r, s);
        require(signer != address(0), "bad sig");

        consentSeen[structHash] = true;
        emit ConsentAnchored(consentHash, signer, issuedAt, nonce);
    }

    // --- views ---
    function revocationCount(address issuer) external view returns (uint256) {
        return revocationBatches[issuer].length;
    }
    function statusBitmapCount(address issuer) external view returns (uint256) {
        return statusBitmaps[issuer].length;
    }
}
