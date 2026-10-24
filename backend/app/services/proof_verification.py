"""
Patent Feature: Privacy-Preserving Proof-of-Service Verification.

Verifies the integrity of edge-computed perceptual hashes submitted
by workers as proof of completed service, WITHOUT requiring the actual
image to be uploaded to the server.

The system:
1. Validates hash format and structure (64-char hex perceptual hash)
2. Checks hash uniqueness (prevents reuse of old proofs)
3. Computes a verification confidence score
4. Records the verification result alongside the booking

Novel Claim:
    "A privacy-preserving service completion verification system using
    edge-computed perceptual image hashing, where proof of work is
    transmitted as a compact hash fingerprint without raw image upload,
    enabling verification without customer privacy violation."
"""
import hmac
import hashlib
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.booking import Booking, BookingStatus
from app.config import settings


# Valid pHash format: 64 hex characters (256-bit hash)
PHASH_PATTERN = re.compile(r"^[0-9a-fA-F]{16,64}$")
HAMMING_THRESHOLD = 6


def get_daily_nonce(worker_id: int, date_str: str) -> str:
    """Hex HMAC-SHA256(key=PROOF_SECRET, msg=f'{worker_id}:{date_str}')"""
    key = settings.PROOF_SECRET.encode('utf-8')
    msg = f"{worker_id}:{date_str}".encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def derive_completion_code(booking_id: int, started_at_iso: str) -> str:
    """6 digits from HMAC-SHA256(PROOF_SECRET, f'{booking_id}:{started_at_iso}') mod 10^6, zero-padded"""
    key = settings.PROOF_SECRET.encode('utf-8')
    msg = f"{booking_id}:{started_at_iso}".encode('utf-8')
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    code_int = int.from_bytes(digest[:4], 'big') % (10 ** 6)
    return str(code_int).zfill(6)


def build_canonical(job_id: int, worker_id: int, photo_hash: str, lat, lon, captured_at: str, nonce_date: str, customer_code: str) -> str:
    """Build the canonical string. lat/lon are floats or None. captured_at is UTC ISO to the second with Z."""
    lat_s = f"{lat:.5f}" if lat is not None else "NA"
    lon_s = f"{lon:.5f}" if lon is not None else "NA"
    return f"v1|{job_id}|{worker_id}|{photo_hash}|{lat_s}|{lon_s}|{captured_at}|{nonce_date}|{customer_code}"


def compute_proof_tag(nonce: str, canonical: str) -> str:
    """HMAC-SHA256 keyed by nonce (as UTF-8 bytes), over canonical string. Returns lowercase hex."""
    return hmac.new(nonce.encode('utf-8'), canonical.encode('utf-8'), hashlib.sha256).hexdigest()


def validate_proof_hash(hash_str: Optional[str]) -> Dict:
    """
    Validate the format and structure of a proof-of-work hash.
    """
    if not hash_str:
        return {"is_valid": False, "format_ok": False, "length": 0, "error": "No hash provided"}

    hash_clean = hash_str.strip()

    if not PHASH_PATTERN.match(hash_clean):
        return {"is_valid": False, "format_ok": False, "length": len(hash_clean), "error": "Hash must be 16-64 hexadecimal characters"}

    return {"is_valid": True, "format_ok": True, "length": len(hash_clean), "error": None}


def hamming_distance(hex1: str, hex2: str) -> int:
    """Calculate the Hamming distance between two hex hashes."""
    try:
        val1 = int(hex1, 16)
        val2 = int(hex2, 16)
        return bin(val1 ^ val2).count('1')
    except Exception:
        return 999


def check_hash_uniqueness(db: Session, hash_str: str, exclude_booking_id: Optional[int] = None) -> bool:
    """
    Check that this proof hash hasn't been used for a different booking.
    Prevents workers from reusing old proof photos by checking Hamming distance.
    Flag as duplicate if Hamming distance <= HAMMING_THRESHOLD.
    """
    query = db.query(Booking).filter(
        Booking.proof_of_work_hash.isnot(None),
        Booking.status == BookingStatus.COMPLETED,
    )

    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)

    existing_bookings = query.all()
    for booking in existing_bookings:
        if booking.proof_of_work_hash and hash_str:
            if hamming_distance(hash_str.strip(), booking.proof_of_work_hash.strip()) <= HAMMING_THRESHOLD:
                return False

    return True


def calculate_verification_confidence(
    before_hash: str,
    after_hash: str,
    privacy_score: Optional[float] = None,
    gps_match: bool = False,
    nonce_match: bool = False,
    customer_otp_match: bool = False
) -> Dict:
    """
    Compute a confidence score for the proof-of-work submission.
    """
    confidence = 0.0
    factors = {}

    # Factor 1: Hash quality (10% weight)
    val_b = validate_proof_hash(before_hash)
    val_a = validate_proof_hash(after_hash)
    if val_b["is_valid"] and val_a["is_valid"]:
        hash_quality = 100.0
        confidence += hash_quality * 0.10
        factors["hash_quality"] = 100.0
    else:
        factors["hash_quality"] = 0.0

    # Factor 2: Privacy compliance (10% weight)
    if privacy_score is not None:
        privacy_quality = min(100.0, max(0.0, privacy_score))
        confidence += privacy_quality * 0.10
        factors["privacy_compliance"] = round(privacy_quality, 1)

    # Factor 3: Cryptographic Nonce (30% weight)
    if nonce_match:
        confidence += 100.0 * 0.30
        factors["nonce_match"] = 100.0

    # Factor 4: GPS Match (20% weight)
    if gps_match:
        confidence += 100.0 * 0.20
        factors["gps_match"] = 100.0

    # Factor 5: Customer OTP (30% weight - strongest signal)
    if customer_otp_match:
        confidence += 100.0 * 0.30
        factors["customer_otp"] = 100.0

    return {
        "confidence": round(min(100.0, max(0.0, confidence)), 1),
        "privacy_grade": "A" if (privacy_score or 50) >= 80 else "B",
        "factors": factors,
    }


def verify_proof_of_work(
    db: Session,
    booking_id: int,
    hash_str: Optional[str],
    privacy_score: Optional[float] = None,
    proof_bundle: Optional[Dict] = None
) -> Dict:
    """
    Complete proof-of-work verification pipeline.
    """
    result = {
        "verified": False,
        "hash_valid": False,
        "hash_unique": False,
        "confidence": 0.0,
        "privacy_grade": "D",
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        "error": None,
    }

    val = validate_proof_hash(hash_str)
    if not val["is_valid"]:
        result["error"] = "Invalid hash format"
        return result
        
    result["hash_valid"] = True

    # 1. Uniqueness Check
    is_unique = check_hash_uniqueness(db, hash_str, exclude_booking_id=booking_id)
    result["hash_unique"] = is_unique

    if not is_unique:
        result["error"] = "This proof hash is too similar to a previous booking (potential replay attack detected)"
        return result

    nonce_match = proof_bundle.get('nonce_match', False) if proof_bundle else False
    gps_match = proof_bundle.get('gps_match', False) if proof_bundle else False
    otp_match = proof_bundle.get('customer_otp_match', False) if proof_bundle else False
    
    confidence_result = calculate_verification_confidence(
        before_hash=hash_str,
        after_hash=hash_str,
        privacy_score=privacy_score,
        nonce_match=nonce_match,
        gps_match=gps_match,
        customer_otp_match=otp_match
    )

    result["confidence"] = confidence_result["confidence"]
    result["privacy_grade"] = confidence_result["privacy_grade"]
    result["verified"] = confidence_result["confidence"] >= 50.0

    return result
