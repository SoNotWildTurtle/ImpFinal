import { createHash } from 'crypto';

export interface RevocationState {
  revokedIds: Set<string>;
  index: Map<string, number>;
}

export function createRevocationState(): RevocationState {
  return { revokedIds: new Set(), index: new Map() };
}

export function includeRevocation(state: RevocationState, vcId: string): void {
  if (!state.index.has(vcId)) {
    state.index.set(vcId, state.index.size);
  }
  state.revokedIds.add(vcId);
}

export function isRevoked(state: RevocationState, vcId: string): boolean {
  return state.revokedIds.has(vcId);
}

export function buildStatusBitmap(state: RevocationState): Uint8Array {
  const size = state.index.size === 0 ? 1 : Math.ceil(state.index.size / 8);
  const bitmap = new Uint8Array(size);
  for (const [vcId, position] of state.index.entries()) {
    if (!state.revokedIds.has(vcId)) continue;
    const byteIndex = Math.floor(position / 8);
    const bitIndex = position % 8;
    bitmap[byteIndex] |= 1 << bitIndex;
  }
  return bitmap;
}

export function buildMerkleRoot(ids: string[]): string {
  if (ids.length === 0) {
    return '0x' + createHash('sha256').update('').digest('hex');
  }
  const leaves = ids
    .slice()
    .sort()
    .map((id) => {
      const cleaned = id.replace(/^0x/, '');
      if (cleaned.length % 2 !== 0) {
        return Buffer.from(cleaned.padStart(cleaned.length + 1, '0'), 'hex');
      }
      try {
        return Buffer.from(cleaned, 'hex');
      } catch {
        return createHash('sha256').update(id).digest();
      }
    });

  let level = leaves.length ? leaves : [Buffer.alloc(32)];
  while (level.length > 1) {
    const next: Buffer[] = [];
    for (let i = 0; i < level.length; i += 2) {
      const left = level[i];
      const right = i + 1 < level.length ? level[i + 1] : Buffer.alloc(32);
      next.push(createHash('sha256').update(Buffer.concat([left, right])).digest());
    }
    level = next;
  }
  return '0x' + level[0].toString('hex');
}

export function bitmapToHex(bitmap: Uint8Array): string {
  return Array.from(bitmap)
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

