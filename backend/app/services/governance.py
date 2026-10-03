"""
Cooperative Democratic Governance — Backend Service

Enables cooperative proposals and worker voting.
Only ADMIN can create proposals. Only VERIFIED workers can vote.
Each worker gets 1 vote per proposal, weighted by trust score.
Results are tamper-evidented with SHA-256 hash of all votes.
"""
from datetime import datetime, timezone
import hashlib
import json
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Boolean
from app.database.session import Base


# ── Models ───────────────────────────────────────────────────────────────────
class CooperativeProposal(Base):
    __tablename__ = "cooperative_proposals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, default="General")  # General, Pricing, Membership, Policy
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE, PASSED, REJECTED, CLOSED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closes_at = Column(DateTime, nullable=True)
    result_hash = Column(String, nullable=True)  # SHA-256 tamper-evident hash
    votes_json = Column(Text, default="[]")  # JSON array of vote records


# ── Service Functions ────────────────────────────────────────────────────────

def create_proposal(db: Session, admin_user_id: int, title: str, description: str, category: str = "General"):
    """Admin creates a new cooperative proposal for worker voting."""
    proposal = CooperativeProposal(
        title=title,
        description=description,
        category=category,
        created_by=admin_user_id,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return {
        "id": proposal.id,
        "title": proposal.title,
        "description": proposal.description,
        "category": proposal.category,
        "status": proposal.status,
        "message": "✅ Proposal created successfully. Verified workers can now vote.",
    }


def list_proposals(db: Session):
    """List all proposals, newest first."""
    proposals = db.query(CooperativeProposal).order_by(CooperativeProposal.created_at.desc()).all()
    results = []
    for p in proposals:
        votes = json.loads(p.votes_json) if p.votes_json else []
        yes_votes = len([v for v in votes if v["vote"] == "YES"])
        no_votes = len([v for v in votes if v["vote"] == "NO"])
        total_votes = len(votes)

        results.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "category": p.category,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "total_votes": total_votes,
            "yes_votes": yes_votes,
            "no_votes": no_votes,
            "yes_weight": yes_votes, # Kept for frontend compatibility
            "total_weight": total_votes,
            "approval_pct": round((yes_votes / total_votes) * 100, 1) if total_votes > 0 else 0,
            "result_hash": p.result_hash,
        })
    return results


def cast_vote(db: Session, proposal_id: int, worker_id: int, worker_name: str, trust_score: float, vote: str):
    """Worker casts a single equal vote on a proposal (One Member, One Vote)."""
    proposal = db.query(CooperativeProposal).filter(CooperativeProposal.id == proposal_id).first()
    if not proposal:
        raise ValueError("Proposal not found.")
    if proposal.status != "ACTIVE":
        raise ValueError(f"Voting is closed. Proposal status: {proposal.status}")

    vote = vote.upper()
    if vote not in ("YES", "NO"):
        raise ValueError("Vote must be YES or NO.")

    votes = json.loads(proposal.votes_json) if proposal.votes_json else []

    # Check for duplicate vote
    for v in votes:
        if v["worker_id"] == worker_id:
            raise ValueError("You have already voted on this proposal.")

    # One Member, One Vote
    weight = 1.0

    # Tamper-evident chaining: Get previous vote's hash or proposal ID
    prev_hash = votes[-1]["vote_hash"] if votes else str(proposal_id)
    
    vote_record = {
        "worker_id": worker_id,
        "worker_name": worker_name,
        "vote": vote,
        "weight": weight,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prev_hash": prev_hash
    }
    
    # Generate chain hash
    vote_record["vote_hash"] = hashlib.sha256(json.dumps(vote_record, sort_keys=True).encode()).hexdigest()
    
    votes.append(vote_record)
    proposal.votes_json = json.dumps(votes)
    proposal.result_hash = vote_record["vote_hash"]

    yes_votes = sum(1 for v in votes if v["vote"] == "YES")
    no_votes = sum(1 for v in votes if v["vote"] == "NO")
    total_votes = len(votes)

    # Simplified Quorum (e.g., minimum 5 votes for a decision)
    # In a real app, query verified workers count and check >= 50%
    from app.models.worker import Worker, VerificationStatus
    total_verified_workers = db.query(Worker).filter(Worker.verification_status == VerificationStatus.VERIFIED).count()
    quorum = max(3, int(total_verified_workers * 0.5))

    if total_votes >= quorum:
        approval = (yes_votes / total_votes) * 100
        if approval > 50.0:
            proposal.status = "PASSED"
        elif (no_votes / total_votes) * 100 >= 50.0:
            proposal.status = "REJECTED"

    db.commit()

    return {
        "message": f"✅ Your vote ({vote}) has been recorded. (One Member, One Vote).",
        "vote": vote,
        "weight": weight,
        "proposal_status": proposal.status,
        "result_hash": proposal.result_hash[:16] + "...",
    }
