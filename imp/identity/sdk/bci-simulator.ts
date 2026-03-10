import { signJWS } from './crypto';
import { makeBCIIntentEnvelope } from './bci-sim';

export interface IntentEnvelope {
  type: 'BCIIntentEnvelope';
  bci_did: string;
  user_did: string;
  session_id: string;
  timestamp: string;
  intent: {
    class: string;
    action: string;
    params: Record<string, unknown>;
  };
  liveness: {
    method: string;
    score: number;
    freshness_ms: number;
  };
  proof: {
    alg: string;
    sig: string;
  };
}

export async function createIntentEnvelope(userDid: string, companionDid: string): Promise<IntentEnvelope> {
  const base = await makeBCIIntentEnvelope({
    bciDid: 'did:bci:demo',
    userDid,
    companionDid,
    action: 'bind_companion',
    scope: ['identity.bind'],
  });
  const sig = await signJWS('did:bci:demo', base);
  return { ...base, proof: { alg: 'Ed25519', sig } };
}

