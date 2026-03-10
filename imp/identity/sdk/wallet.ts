import { randomUUID } from 'crypto';
import { signJWS } from '../issuer-service/did';

export type ConsentReceipt = {
  consent_id: string;
  user_did: string;
  action: string;
  companion_did: string;
  scope: string[];
  timestamp: string;
};

export class Wallet {
  constructor(public readonly userDid: string) {}

  async consentUI(summary: string): Promise<boolean> {
    return Boolean(summary);
  }

  async createConsentReceipt(companionDid: string, action: string, scope: string[]): Promise<ConsentReceipt> {
    return {
      consent_id: `urn:consent:${randomUUID()}`,
      user_did: this.userDid,
      action,
      companion_did: companionDid,
      scope,
      timestamp: new Date().toISOString(),
    };
  }

  async signConsentJWS(payload: object): Promise<string> {
    return signJWS(this.userDid, payload);
  }

  async presentVP(request: unknown, vcs: unknown[]): Promise<string> {
    const vp = {
      '@context': ['https://www.w3.org/2018/credentials/v1'],
      type: ['VerifiablePresentation'],
      request,
      verifiableCredential: vcs,
    };
    return signJWS(this.userDid, vp);
  }
}

