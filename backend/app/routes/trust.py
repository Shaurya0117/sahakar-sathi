"""
Trust Score API Routes.

Patent Feature: Composite Verifiable Trust Score — endpoints for
viewing detailed trust score breakdowns for cooperative workers.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.worker import Worker
from app.services.trust_score import calculate_trust_score

trust_router = APIRouter(prefix="/trust", tags=["Trust Score"])


@trust_router.get(
    "/workers/{worker_id}",
    summary="Get detailed trust score breakdown for a worker",
)
def get_worker_trust_score(
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Patent Feature: Composite Verifiable Trust Score.

    Returns the full 7-factor trust breakdown for a specific worker:
    - Customer Satisfaction, Reliability, Punctuality, Skill Breadth,
      Proof Compliance, Economic Equity, Cooperative Tenure
    - Composite score (0-100) and trust tier (NEW/BRONZE/SILVER/GOLD/PLATINUM)
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found.")

    trust_data = calculate_trust_score(db, worker)
    user = worker.user

    return {
        "worker_id": worker.id,
        "worker_name": user.name if user else f"Worker #{worker.id}",
        "profession": worker.profession,
        "rating": worker.rating,
        "total_jobs": worker.total_jobs,
        "trust": trust_data,
    }
