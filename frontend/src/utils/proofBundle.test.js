import { describe, it, expect } from 'vitest';
import { buildCanonical, computeTag } from './proofBundle';
import vec from '../../../backend/tests/fixtures/proof_vector.json';

describe('Proof Bundle Verification', () => {
  it('buildCanonical matches cross-language fixture', () => {
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
    expect(canonical).toBe(vec.expected_canonical);
  });

  it('computeTag matches cross-language fixture', async () => {
    const tag = await computeTag(vec.expected_nonce, vec.expected_canonical);
    expect(tag).toBe(vec.expected_tag);
  });
});
