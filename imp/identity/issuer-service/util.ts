import { createHash } from 'crypto';

export function nowSec(): number {
  return Math.floor(Date.now() / 1000);
}

export function sha256hex(data: Uint8Array | string): string {
  let buffer: Buffer;
  if (typeof data === 'string') {
    if (data.startsWith('0x')) {
      const cleaned = data.slice(2);
      buffer = Buffer.from(cleaned.length % 2 === 0 ? cleaned : `0${cleaned}`, 'hex');
    } else {
      buffer = Buffer.from(data, 'utf8');
    }
  } else {
    buffer = Buffer.from(data);
  }
  return createHash('sha256').update(buffer).digest('hex');
}

