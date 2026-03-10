export async function resolveIssuerPolicy(issuerDid: string): Promise<{ allowed: boolean }> {
  return { allowed: issuerDid.startsWith('did:') };
}

export async function fetchRevocationProof(vcId: string): Promise<boolean> {
  return Boolean(vcId);
}

