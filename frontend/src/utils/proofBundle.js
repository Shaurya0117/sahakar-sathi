/**
 * Pure functions for proof bundle construction.
 * No image data is ever included.
 */

export function buildCanonical(fields) {
  const { jobId, workerId, photoHash, lat, lon, capturedAt, nonceDate, customerCode } = fields;
  const latS = (lat != null) ? lat.toFixed(5) : 'NA';
  const lonS = (lon != null) ? lon.toFixed(5) : 'NA';
  return `v1|${jobId}|${workerId}|${photoHash}|${latS}|${lonS}|${capturedAt}|${nonceDate}|${customerCode}`;
}

export async function computeTag(nonceHex, canonicalString) {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(nonceHex),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', keyMaterial, enc.encode(canonicalString));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}
