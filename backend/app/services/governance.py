"""
Cooperative Democratic Governance — Backend Service

Enables cooperative proposals and worker voting.
Only ADMIN can create proposals. Only VERIFIED workers can vote.
Each worker gets 1 vote per proposal, weighted by trust score.
Results are tamper-proofed with SHA-256 hash of all votes.
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
    result_hash = Column(String, nullable=True)  # SHA-256 tamper-proof hash
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
        yes_votes = [v for v in votes if v["vote"] == "YES"]
        no_votes = [v for v in votes if v["vote"] == "NO"]
        total_weight = sum(v.get("weight", 1) for v in votes)
        yes_weight = sum(v.get("weight", 1) for v in yes_votes)

        results.append({
            "id": p.id,
            "title": p.title,
            "description": p.description,
            "category": p.category,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "total_votes": len(votes),
            "yes_votes": len(yes_votes),
            "no_votes": len(no_votes),
            "yes_weight": round(yes_weight, 2),
            "total_weight": round(total_weight, 2),
            "approval_pct": round((yes_weight / total_weight) * 100, 1) if total_weight > 0 else 0,
            "result_hash": p.result_hash,
        })
    return results


def cast_vote(db: Session, proposal_id: int, worker_id: int, worker_name: str, trust_score: float, vote: str):
    """Worker casts a weighted vote on a proposal."""
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

    # Weight vote by trust score (1.0 to 3.0)
    weight = 1.0
    if trust_score >= 90:
        weight = 3.0
    elif trust_score >= 75:
        weight = 2.0
    elif trust_score >= 60:
        weight = 1.5

    vote_record = {
        "worker_id": worker_id,
        "worker_name": worker_name,
        "vote": vote,
        "weight": weight,
        "trust_score": trust_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    votes.append(vote_record)
    proposal.votes_json = json.dumps(votes)

    # Compute tamper-proof hash of all votes
    vote_data = json.dumps(votes, sort_keys=True)
    proposal.result_hash = hashlib.sha256(vote_data.encode()).hexdigest()

    # Auto-resolve if enough votes (e.g., 5+ votes and clear majority)
    yes_weight = sum(v.get("weight", 1) for v in votes if v["vote"] == "YES")
    no_weight = sum(v.get("weight", 1) for v in votes if v["vote"] == "NO")
    total_weight = yes_weight + no_weight

    if len(votes) >= 3 and total_weight > 0:
        approval = (yes_weight / total_weight) * 100
        if approval >= 66.7:
            proposal.status = "PASSED"
        elif (no_weight / total_weight) * 100 >= 66.7:
            proposal.status = "REJECTED"

    db.commit()

    return {
        "message": f"✅ Your vote ({vote}) has been recorded with weight {weight}x (Trust: {trust_score}).",
        "vote": vote,
        "weight": weight,
        "proposal_status": proposal.status,
        "result_hash": proposal.result_hash[:16] + "...",
    }
