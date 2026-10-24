import json
import os
import hmac
import hashlib
from app.services.proof_verification import (
    get_daily_nonce,
    build_canonical,
    compute_proof_tag,
)
from app.config import settings

def test_proof_vector_python(monkeypatch):
    fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures", "proof_vector.json")
    with open(fixtures_path, "r", encoding="utf-8") as f:
        vec = json.load(f)

    monkeypatch.setattr(settings, "PROOF_SECRET", vec["proof_secret"])

    # 1. Nonce calculation
    nonce = get_daily_nonce(vec["worker_id"], vec["nonce_date"])
    assert nonce == vec["expected_nonce"]

    # 2. Canonical string
    canonical = build_canonical(
        job_id=vec["job_id"],
        worker_id=vec["worker_id"],
        photo_hash=vec["photo_hash"],
        lat=vec["lat"],
        lon=vec["lon"],
        captured_at=vec["captured_at"],
        nonce_date=vec["nonce_date"],
        customer_code=vec["customer_code"],
    )
    assert canonical == vec["expected_canonical"]

    # 3. Proof tag
    tag = compute_proof_tag(nonce, canonical)
    assert tag == vec["expected_tag"]
