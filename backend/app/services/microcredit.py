"""
Cooperative Micro-Credit System — Backend Service

Workers with high trust scores can request salary advances (micro-loans)
from the cooperative fund. Loan eligibility and limits are determined by
the worker's trust tier:
  - PLATINUM (90+): Up to ₹10,000
  - GOLD (75+):     Up to ₹5,000
  - SILVER (60+):   Up to ₹2,000
  - Below SILVER:   Not eligible

Loans are auto-repaid by deducting 20% from each future completed job.
"""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from app.database.session import Base
import json


# ── Model ────────────────────────────────────────────────────────────────────
class MicroLoan(Base):
    __tablename__ = "micro_loans"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    repaid_amount = Column(Float, default=0.0)
    status = Column(String, default="ACTIVE")  # ACTIVE, REPAID, DEFAULTED
    purpose = Column(String, default="Salary Advance")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    repaid_at = Column(DateTime, nullable=True)
    repayment_log = Column(Text, default="[]")  # JSON array of deductions


# ── Service Functions ────────────────────────────────────────────────────────

TIER_LIMITS = {
    "PLATINUM": 10000,
    "GOLD": 5000,
    "SILVER": 2000,
}

def _get_trust_tier(score: float) -> str:
    if score >= 90: return "PLATINUM"
    if score >= 75: return "GOLD"
    if score >= 60: return "SILVER"
    if score >= 40: return "BRONZE"
    return "NEW"


def check_eligibility(db: Session, worker):
    """Check if a worker is eligible for a micro-loan and return details."""
    trust_score = worker.trust_score or 0
    tier = _get_trust_tier(trust_score)
    max_amount = TIER_LIMITS.get(tier, 0)

    # Check existing active loans
    active_loan = db.query(MicroLoan).filter(
        MicroLoan.worker_id == worker.id,
        MicroLoan.status == "ACTIVE"
    ).first()

    outstanding = 0
    if active_loan:
        outstanding = active_loan.amount - active_loan.repaid_amount

    return {
        "eligible": max_amount > 0 and not active_loan,
        "trust_score": trust_score,
        "trust_tier": tier,
        "max_loan_amount": max_amount,
        "has_active_loan": active_loan is not None,
        "outstanding_balance": round(outstanding, 2),
        "repayment_rate": "20% auto-deducted from each completed job",
        "active_loan": {
            "id": active_loan.id,
            "amount": active_loan.amount,
            "repaid": round(active_loan.repaid_amount, 2),
            "remaining": round(active_loan.amount - active_loan.repaid_amount, 2),
            "progress_pct": round((active_loan.repaid_amount / active_loan.amount) * 100, 1) if active_loan.amount > 0 else 0,
            "status": active_loan.status,
            "created_at": active_loan.created_at.isoformat() if active_loan.created_at else None,
        } if active_loan else None,
    }


def apply_for_loan(db: Session, worker, amount: float, purpose: str = "Salary Advance"):
    """Worker applies for a micro-loan from the cooperative fund."""
    trust_score = worker.trust_score or 0
    tier = _get_trust_tier(trust_score)
    max_amount = TIER_LIMITS.get(tier, 0)

    if max_amount == 0:
        raise ValueError(f"Not eligible. Trust tier {tier} does not qualify for micro-credit. Minimum: SILVER (60+).")

    # Check for active loan
    active = db.query(MicroLoan).filter(
        MicroLoan.worker_id == worker.id,
        MicroLoan.status == "ACTIVE"
    ).first()
    if active:
        raise ValueError(f"You already have an active loan of ₹{active.amount}. Repay it first.")

    if amount <= 0 or amount > max_amount:
        raise ValueError(f"Loan amount must be between ₹1 and ₹{max_amount} for {tier} tier.")

    loan = MicroLoan(
        worker_id=worker.id,
        amount=amount,
        purpose=purpose,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    return {
        "loan_id": loan.id,
        "amount": loan.amount,
        "purpose": loan.purpose,
        "status": loan.status,
        "message": f"✅ Micro-loan of ₹{int(loan.amount)} approved instantly! 20% will be auto-deducted from your future completed jobs.",
        "repayment_rate": "20% per completed job",
    }


def get_my_loans(db: Session, worker_id: int):
    """Get all loans for a worker."""
    loans = db.query(MicroLoan).filter(MicroLoan.worker_id == worker_id).order_by(MicroLoan.created_at.desc()).all()
    return [{
        "id": l.id,
        "amount": l.amount,
        "repaid": round(l.repaid_amount, 2),
        "remaining": round(l.amount - l.repaid_amount, 2),
        "progress_pct": round((l.repaid_amount / l.amount) * 100, 1) if l.amount > 0 else 0,
        "status": l.status,
        "purpose": l.purpose,
        "created_at": l.created_at.isoformat() if l.created_at else None,
        "repaid_at": l.repaid_at.isoformat() if l.repaid_at else None,
    } for l in loans]
