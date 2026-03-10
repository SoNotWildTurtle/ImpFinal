export interface ConsentContext {
  companion_did: string;
  user_did: string;
  model_hash: string;
}

export async function verifyDIDJWS(jws: any, context: ConsentContext): Promise<boolean> {
  if (!jws) return false;
  try {
    const payload = typeof jws === 'string' ? JSON.parse(Buffer.from(jws.split('.')[1] || '', 'base64url').toString('utf8') || '{}') : jws;
    return (
      payload?.companion_did === context.companion_did &&
      payload?.user_did === context.user_did &&
      payload?.model_hash === context.model_hash
    );
  } catch {
    return false;
  }
}

export async function signJWS(_: string, payload: object): Promise<string> {
  const body = Buffer.from(JSON.stringify(payload), 'utf8').toString('base64url');
  return `stub.${body}.sig`;
}

