import { ethers } from 'ethers';

export async function anchorConsentTyped(
  consentHashHex: string,
  issuedAt: number,
  nonce: number,
  signature: string,
) {
  console.log('anchor consent', { consentHashHex, issuedAt, nonce, signature });
}

export async function postRevocationRoot(root: string) {
  console.log('posting revocation root', root);
}

export async function postStatusBitmap(contentHashHex: string, length: number) {
  console.log('posting status bitmap', { contentHashHex, length });
}

