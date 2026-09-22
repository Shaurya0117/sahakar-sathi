"""
Peer Verification API Routes.

Patent Feature: Decentralized Peer Verification Protocol.
Endpoints for existing verified workers to vote on pending workers.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from app.auth.dependencies import require_worker
from app.database.session import get_db
from app.models.user import User
from app.models.worker import Worker, VerificationStatus
from app.services.peer_verification import submit_peer_vote, calculate_consensus

peer_router = APIRouter(prefix="/peer-verification", tags=["Peer Verification"])

class VoteRequest(BaseModel):
    candidate_id: int
    is_positive: bool


@peer_router.get("/candidates", summary="List pending workers needing verification")
def list_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_worker),
):
    """
    Returns a list of workers who are PENDING verification.
    Only VERIFIED workers can access this endpoint.
    """
    voter = db.query(Worker).filter(Worker.user_id == current_user.id).first()
    if not voter or voter.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(status_code=403, detail="Only verified workers can view candidates.")
        
    candidates = db.query(Worker).filter(
        Worker.verification_status == VerificationStatus.PENDING,
        Worker.id != voter.id
    ).all()
    
    results = []
    for c in candidates:
        consensus = calculate_consensus(c)
        user = c.user
        
        # Check if current user already voted
        voted = False
        if c.peer_votes:
            votes = json.loads(c.peer_votes) if isinstance(c.peer_votes, str) else c.peer_votes
            if any(v.get("voter_id") == voter.id for v in votes):
                voted = True
                
        results.append({
            "worker_id": c.id,
            "name": user.name if user else f"Worker #{c.id}",
            "profession": c.profession,
            "location": c.location,
            "experience_years": c.experience_years,
            "consensus_score": consensus["score"],
            "total_votes": consensus["total_votes"],
            "has_voted": voted
        })
        
    return results


@peer_router.post("/vote", summary="Submit a verification vote for a candidate")
def vote_for_candidate(
    payload: VoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_worker),
):
    """
    Submit a positive or negative vote for a pending worker.
    """
    voter = db.query(Worker).filter(Worker.user_id == current_user.id).first()
    if not voter:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
        
    try:
        result = submit_peer_vote(db, voter.id, payload.candidate_id, payload.is_positive)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
