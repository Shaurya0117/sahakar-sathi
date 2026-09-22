"""
Cooperative Governance API Routes

Endpoints:
  GET  /api/governance/proposals            — List all proposals
  POST /api/governance/proposals            — Create proposal (ADMIN)
  POST /api/governance/proposals/{id}/vote  — Cast vote (WORKER, verified)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.dependencies import require_admin, require_worker
from app.models.worker import Worker
from app.models.user import User
from app.services.governance import create_proposal, list_proposals, cast_vote

router = APIRouter(prefix="/governance", tags=["Cooperative Governance"])


class ProposalCreate(BaseModel):
    title: str
    description: str
    category: str = "General"


class VoteBody(BaseModel):
    vote: str  # "YES" or "NO"


@router.get("/proposals")
def get_proposals(db: Session = Depends(get_db)):
    """List all cooperative proposals (accessible to all authenticated users)."""
    return list_proposals(db)


@router.post("/proposals")
def post_proposal(body: ProposalCreate, user=Depends(require_admin), db: Session = Depends(get_db)):
    """Admin creates a new cooperative proposal."""
    return create_proposal(db, user.id, body.title, body.description, body.category)


@router.post("/proposals/{proposal_id}/vote")
def vote_on_proposal(proposal_id: int, body: VoteBody, user=Depends(require_worker), db: Session = Depends(get_db)):
    """Verified worker casts a weighted vote on a proposal."""
    worker = db.query(Worker).filter(Worker.user_id == user.id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
    if worker.verification_status != "VERIFIED":
        raise HTTPException(status_code=403, detail="Only verified cooperative members can vote.")
    try:
        return cast_vote(db, proposal_id, worker.id, user.name, worker.trust_score or 0, body.vote)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
