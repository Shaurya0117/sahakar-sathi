"""
Equity Dashboard API Routes.

Patent Feature: Cooperative Workload Equity Graph — admin-only endpoints
for viewing cooperative-wide fairness analytics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models.user import User
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.matching.equity_graph import (
    calculate_equity_score,
    get_cooperative_equity_dashboard,
)

equity_router = APIRouter(prefix="/equity", tags=["Equity Graph"])


@equity_router.get(
    "/dashboard",
    summary="Get cooperative-wide equity analytics dashboard (ADMIN only)",
)
def get_equity_dashboard(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Patent Feature: Cooperative Workload Equity Graph Dashboard.

    Returns multi-dimensional fairness analytics across all cooperative workers:
    - Per-worker equity scores (income parity, geographic burden, skill utilization,
      temporal fairness, fatigue capacity)
    - Cooperative-wide averages and inequality index
    - Count of fatigued/blocked workers
    """
    workers = db.query(Worker).filter(
        Worker.verification_status == VerificationStatus.VERIFIED,
    ).all()

    dashboard = get_cooperative_equity_dashboard(db, workers)
    return dashboard


@equity_router.get(
    "/workers/{worker_id}",
    summary="Get detailed equity breakdown for a specific worker (ADMIN only)",
)
def get_worker_equity(
    worker_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Returns the full equity graph breakdown for a single worker.
    """
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Worker not found.")

    equity = calculate_equity_score(db, worker)
    user = worker.user
    return {
        "worker_id": worker.id,
        "worker_name": user.name if user else f"Worker #{worker.id}",
        "profession": worker.profession,
        "total_jobs": worker.total_jobs,
        "equity": equity,
    }
