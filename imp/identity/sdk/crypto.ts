export async function verifyJWS(token: string): Promise<{ header: any; payload: any }> {
  const parts = token.split('.');
  if (parts.length < 3) {
    throw new Error('invalid_jws');
  }
  const payload = JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf8'));
  return { header: { alg: 'EdDSA' }, payload };
}

function encodePayload(payload: object): string {
  return Buffer.from(JSON.stringify(payload), 'utf8').toString('base64url');
}

export async function signJWS(_: string, payload: object): Promise<string> {
  const body = encodePayload(payload);
  return `stub.${body}.sig`;
}

export async function sign(subjectDid: string, payload: object): Promise<string> {
  const body = encodePayload(payload);
  return `sig.${subjectDid}.${body}`;
}

export async function resolveDIDKeys(_: string): Promise<string[]> {
  return ['did:example:issuer#keys-1'];
}

