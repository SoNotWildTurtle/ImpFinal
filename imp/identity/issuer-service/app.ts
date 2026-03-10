import Fastify from 'fastify';
import { verifyDIDJWS } from './did';
import { verifyTEEQuote } from './tee';
import { signVC } from './vc';
import { anchorConsentTyped, postRevocationRoot, postStatusBitmap } from './chain';
import {
  createRevocationState,
  includeRevocation,
  isRevoked,
  buildStatusBitmap,
  buildMerkleRoot,
} from './revocation';
import { nowSec, sha256hex } from './util';

const app = Fastify({ logger: true });

const revocationState = createRevocationState();
let currentBitmap = new Uint8Array(0);

app.post('/register-companion', async (req, reply) => {
  const {
    companion_did,
    attestation_quote,
    model_hash,
    user_did,
    consent_jws,
    consent_anchor,
  } = req.body as any;

  const consentOk = await verifyDIDJWS(consent_jws, {
    companion_did,
    user_did,
    model_hash,
  });
  if (!consentOk) {
    return reply.code(400).send({ error: 'invalid_consent' });
  }

  const attestation = await verifyTEEQuote(attestation_quote, { expectedModelHash: model_hash });
  if (!attestation.ok) {
    return reply.code(400).send({ error: 'bad_attestation', detail: attestation.detail });
  }

  const vc = await signVC({
    type: ['VerifiableCredential', 'CompanionBindingCredential'],
    subject: {
      id: companion_did,
      user: user_did,
      companionVersion: attestation.runtimeVersion,
      attestation: {
        teehash: attestation.reportDigest,
        attestTime: new Date().toISOString(),
      },
    },
  });

  if (consent_anchor?.consentHash && consent_anchor?.sig) {
    await anchorConsentTyped(
      consent_anchor.consentHash,
      consent_anchor.issuedAt ?? nowSec(),
      consent_anchor.nonce ?? 0,
      consent_anchor.sig,
    );
  }

  return reply.send({ status: 'issued', vc });
});

app.post('/revoke', async (req, reply) => {
  const { vc_id } = req.body as any;
  includeRevocation(revocationState, vc_id);

  const merkleRoot = buildMerkleRoot(Array.from(revocationState.revokedIds));
  await postRevocationRoot(merkleRoot);

  currentBitmap = buildStatusBitmap(revocationState);
  const bitmapHash = sha256hex(currentBitmap);
  await postStatusBitmap(`0x${bitmapHash}`, currentBitmap.length);

  return reply.send({
    ok: true,
    merkleRoot,
    statusBitmapHash: `0x${bitmapHash}`,
  });
});

app.post('/status', async (req, reply) => {
  const { vc_id } = req.body as any;
  return reply.send({ revoked: isRevoked(revocationState, vc_id) });
});

app.listen({ port: 8080 });

