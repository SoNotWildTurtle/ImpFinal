import { resolveIssuerPolicy, fetchRevocationProof } from './network';
import { verifyJWS } from './crypto';

export class Verifier {
  async verifyPresentation(vpJWS: string): Promise<boolean> {
    const { payload } = await verifyJWS(vpJWS);
    const credentials: any[] = payload?.verifiableCredential ?? [];
    for (const credential of credentials) {
      const issuer = credential?.issuer;
      if (!issuer) throw new Error('missing issuer');
      const policy = await resolveIssuerPolicy(issuer);
      if (!policy.allowed) throw new Error('issuer not allowed');
      const proofOk = await fetchRevocationProof(credential?.id);
      if (!proofOk) throw new Error('credential revoked');
    }
    return true;
  }
}

