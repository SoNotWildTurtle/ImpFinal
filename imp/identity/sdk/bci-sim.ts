import { randomUUID } from 'crypto';
import { sign } from './crypto';

export interface MinimalIntentEnvelope {
  type: 'BCIIntentEnvelope';
  bci_did: string;
  user_did: string;
  session_id: string;
  timestamp: string;
  intent: {
    class: 'CONSENT';
    action: string;
    params: {
      companion_did: string;
      scope: string[];
    };
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

export async function makeBCIIntentEnvelope({
  bciDid,
  userDid,
  companionDid,
  action,
  scope,
}: {
  bciDid: string;
  userDid: string;
  companionDid: string;
  action: string;
  scope: string[];
}): Promise<MinimalIntentEnvelope> {
  const envelope = {
    type: 'BCIIntentEnvelope' as const,
    bci_did: bciDid,
    user_did: userDid,
    session_id: `urn:uuid:${randomUUID()}`,
    timestamp: new Date().toISOString(),
    intent: {
      class: 'CONSENT' as const,
      action,
      params: { companion_did: companionDid, scope },
    },
    liveness: { method: 'local-biometric', score: 0.997, freshness_ms: 600 },
  };

  const sig = await sign(bciDid, envelope);
  return {
    ...envelope,
    proof: { alg: 'Ed25519', sig },
  };
}
