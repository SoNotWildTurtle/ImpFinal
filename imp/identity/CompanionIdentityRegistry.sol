// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Companion Identity Registry (revocations + consent anchors + issuer allowlist)
/// @notice Mirrors the scaffold discussed in the identity-verification design notes.
contract CompanionIdentityRegistry {
    address public owner;

    struct RevocationBatch {
        bytes32 merkleRoot;
        uint256 timestamp;
    }

    mapping(address => bool) public trustedIssuer;
    mapping(address => RevocationBatch[]) public revocationBatches;

    event OwnerChanged(address indexed newOwner);
    event IssuerUpdated(address indexed issuer, bool allowed);
    event RevocationRootPosted(address indexed issuer, bytes32 merkleRoot, uint256 index);
    event ConsentAnchored(bytes32 indexed consentHash, address indexed submitter);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyIssuer() {
        require(trustedIssuer[msg.sender], "issuer not allowed");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setOwner(address newOwner) external onlyOwner {
        owner = newOwner;
        emit OwnerChanged(newOwner);
    }

    function setIssuer(address issuer, bool allowed) external onlyOwner {
        trustedIssuer[issuer] = allowed;
        emit IssuerUpdated(issuer, allowed);
    }

    function postRevocationRoot(bytes32 merkleRoot) external onlyIssuer {
        revocationBatches[msg.sender].push(RevocationBatch({
            merkleRoot: merkleRoot,
            timestamp: block.timestamp
        }));
        emit RevocationRootPosted(msg.sender, merkleRoot, revocationBatches[msg.sender].length - 1);
    }

    function anchorConsent(bytes32 consentHash) external {
        emit ConsentAnchored(consentHash, msg.sender);
    }

    function getRevocationBatch(address issuer, uint256 index) external view returns (bytes32 root, uint256 ts) {
        RevocationBatch storage b = revocationBatches[issuer][index];
        return (b.merkleRoot, b.timestamp);
    }

    function revocationCount(address issuer) external view returns (uint256) {
        return revocationBatches[issuer].length;
    }
}

