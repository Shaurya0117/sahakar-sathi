import { createHmac } from 'crypto';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

// Inline the pure functions (don't import from proofBundle.js due to ESM/browser split)
function buildCanonical(fields) {
  const { jobId, workerId, photoHash, lat, lon, capturedAt, nonceDate, customerCode } = fields;
  const latS = (lat != null) ? lat.toFixed(5) : 'NA';
  const lonS = (lon != null) ? lon.toFixed(5) : 'NA';
  return `v1|${jobId}|${workerId}|${photoHash}|${latS}|${lonS}|${capturedAt}|${nonceDate}|${customerCode}`;
}

function computeTagNode(nonceHex, canonicalString) {
  return createHmac('sha256', Buffer.from(nonceHex, 'utf8'))
    .update(canonicalString, 'utf8')
    .digest('hex');
}

function computeNonce(secret, workerId, dateStr) {
  return createHmac('sha256', Buffer.from(secret, 'utf8'))
    .update(`${workerId}:${dateStr}`, 'utf8')
    .digest('hex');
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const vec = JSON.parse(readFileSync(join(__dirname, '../../backend/tests/fixtures/proof_vector.json'), 'utf8'));

const nonce = computeNonce(vec.proof_secret, vec.worker_id, vec.nonce_date);
const canonical = buildCanonical({
  jobId: vec.job_id,
  workerId: vec.worker_id,
  photoHash: vec.photo_hash,
  lat: vec.lat,
  lon: vec.lon,
  capturedAt: vec.captured_at,
  nonceDate: vec.nonce_date,
  customerCode: vec.customer_code,
});
const tag = computeTagNode(nonce, canonical);

console.log('Nonce:', nonce);
console.log('Canonical:', canonical);
console.log('Tag:', tag);
console.log('Expected nonce:', vec.expected_nonce);
console.log('Expected tag:', vec.expected_tag);

if (nonce !== vec.expected_nonce) {
  console.error('FAIL: nonce mismatch');
  process.exit(1);
}
if (tag !== vec.expected_tag) {
  console.error('FAIL: tag mismatch');
  process.exit(1);
}
console.log('PASS: Both nonce and tag match the vector.');
