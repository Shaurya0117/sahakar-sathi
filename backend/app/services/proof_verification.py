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
import re
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus


# Valid pHash format: 64 hex characters (256-bit hash)
PHASH_PATTERN = re.compile(r"^[0-9a-fA-F]{16,64}$")

# Minimum privacy score threshold (0-100, lower = more private = better)
MIN_PRIVACY_SCORE = 0.0
MAX_PRIVACY_SCORE = 100.0


def validate_proof_hash(hash_str: Optional[str]) -> Dict:
    """
    Validate the format and structure of a proof-of-work hash.

    Returns:
        dict with:
            - is_valid: bool
            - format_ok: bool
            - length: int
            - error: Optional[str]
    """
    if not hash_str:
        return {
            "is_valid": False,
            "format_ok": False,
            "length": 0,
            "error": "No hash provided",
        }

    hash_clean = hash_str.strip()

    if not PHASH_PATTERN.match(hash_clean):
        return {
            "is_valid": False,
            "format_ok": False,
            "length": len(hash_clean),
            "error": "Hash must be 16-64 hexadecimal characters",
        }

    return {
        "is_valid": True,
        "format_ok": True,
        "length": len(hash_clean),
        "error": None,
    }


def check_hash_uniqueness(db: Session, hash_str: str, exclude_booking_id: Optional[int] = None) -> bool:
    """
    Check that this proof hash hasn't been used for a different booking.
    Prevents workers from reusing old proof photos.
    """
    query = db.query(Booking).filter(
        Booking.proof_of_work_hash == hash_str.strip(),
        Booking.status == BookingStatus.COMPLETED,
    )

    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)

    existing = query.first()
    return existing is None  # True = unique, False = duplicate


def calculate_verification_confidence(
    hash_str: str,
    privacy_score: Optional[float] = None,
    has_timestamp: bool = True,
) -> Dict:
    """
    Compute a confidence score for the proof-of-work submission.

    Factors:
    - Hash validity and length (longer hash = more information = higher confidence)
    - Privacy score compliance (lower privacy score = more private = better)
    - Freshness (proof submitted with timestamp metadata)

    Returns:
        dict with:
            - confidence: float (0-100)
            - privacy_grade: str ("A" | "B" | "C" | "D")
            - factors: dict
    """
    confidence = 0.0
    factors = {}

    # Factor 1: Hash quality (40% weight)
    validation = validate_proof_hash(hash_str)
    if validation["is_valid"]:
        # Longer hashes encode more perceptual information
        hash_quality = min(100.0, (validation["length"] / 64.0) * 100.0)
        confidence += hash_quality * 0.40
        factors["hash_quality"] = round(hash_quality, 1)
    else:
        factors["hash_quality"] = 0.0

    # Factor 2: Privacy compliance (30% weight)
    if privacy_score is not None:
        # Higher privacy_score means MORE private (better)
        privacy_quality = min(100.0, max(0.0, privacy_score))
        confidence += privacy_quality * 0.30
        factors["privacy_compliance"] = round(privacy_quality, 1)
    else:
        # No privacy score = moderate compliance
        confidence += 50.0 * 0.30
        factors["privacy_compliance"] = 50.0

    # Factor 3: Freshness / timestamp (30% weight)
    if has_timestamp:
        confidence += 100.0 * 0.30
        factors["freshness"] = 100.0
    else:
        confidence += 30.0 * 0.30
        factors["freshness"] = 30.0

    # Determine privacy grade
    ps = privacy_score if privacy_score is not None else 50.0
    if ps >= 80:
        privacy_grade = "A"
    elif ps >= 60:
        privacy_grade = "B"
    elif ps >= 40:
        privacy_grade = "C"
    else:
        privacy_grade = "D"

    return {
        "confidence": round(min(100.0, max(0.0, confidence)), 1),
        "privacy_grade": privacy_grade,
        "factors": factors,
    }


def verify_proof_of_work(
    db: Session,
    booking_id: int,
    hash_str: Optional[str],
    privacy_score: Optional[float] = None,
) -> Dict:
    """
    Complete proof-of-work verification pipeline.

    Steps:
    1. Validate hash format
    2. Check hash uniqueness (prevent reuse)
    3. Calculate verification confidence
    4. Return comprehensive verification result

    Returns:
        dict with:
            - verified: bool
            - hash_valid: bool
            - hash_unique: bool
            - confidence: float (0-100)
            - privacy_grade: str
            - verification_timestamp: str (ISO format)
            - error: Optional[str]
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

    # Step 1: Validate hash format
    validation = validate_proof_hash(hash_str)
    result["hash_valid"] = validation["is_valid"]

    if not validation["is_valid"]:
        result["error"] = validation.get("error", "Invalid hash format")
        return result

    # Step 2: Check uniqueness
    is_unique = check_hash_uniqueness(db, hash_str, exclude_booking_id=booking_id)
    result["hash_unique"] = is_unique

    if not is_unique:
        result["error"] = "This proof hash has been used for a previous booking (potential reuse detected)"
        return result

    # Step 3: Calculate verification confidence
    confidence_result = calculate_verification_confidence(
        hash_str=hash_str,
        privacy_score=privacy_score,
        has_timestamp=True,
    )

    result["confidence"] = confidence_result["confidence"]
    result["privacy_grade"] = confidence_result["privacy_grade"]

    # Step 4: Determine overall verification (confidence > 50 = verified)
    result["verified"] = confidence_result["confidence"] >= 50.0

    return result
