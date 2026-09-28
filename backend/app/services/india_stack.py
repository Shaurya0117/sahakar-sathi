"""
India Stack Integration Service

Mocks the verification of unorganized workers using e-Shram UAN and DigiLocker APIs.
This grants them instant platform verification and links them to welfare schemes.
"""
from sqlalchemy.orm import Session
from app.models.worker import Worker

def verify_eshram_uan(db: Session, worker: Worker, uan_number: str) -> dict:
    """
    Simulate a call to India Stack (DigiLocker / e-Shram API).
    In a real scenario, this would exchange tokens and fetch verifiable credentials.
    """
    if not uan_number or len(uan_number) < 12:
        raise ValueError("Invalid UAN. Must be at least 12 digits.")
        
    if worker.digilocker_verified:
        raise ValueError("Profile is already verified via India Stack.")

    # Mock fetching benefits based on UAN
    linked_benefits = [
        "PM Suraksha Bima Yojana (PMSBY)",
        "Ayushman Bharat PM-JAY",
        "National Pension Scheme (Traders & Self Employed)"
    ]

    # Update worker profile
    worker.eshram_uan = uan_number
    worker.digilocker_verified = 1
    worker.government_benefits_linked = linked_benefits
    worker.verification_status = "VERIFIED"
    
    # Trust score boost for official government verification
    if worker.trust_score is None:
        worker.trust_score = 65.0  # Silver instantly
        worker.trust_breakdown = {
            "identity_verification": 100,
            "reliability": 50,
            "experience": 50
        }
    else:
        worker.trust_score = min(100.0, worker.trust_score + 15.0)

    db.commit()
    db.refresh(worker)

    return {
        "status": "success",
        "message": "Identity officially verified via DigiLocker.",
        "benefits_linked": linked_benefits,
        "trust_score": worker.trust_score
    }
