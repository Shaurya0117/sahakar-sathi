from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_worker
from app.database.session import get_db
from app.models.user import User
from app.models.worker import Worker
from app.services.proof_verification import get_daily_nonce

proof_router = APIRouter(tags=["Proof of Completion"])

IST = timezone(timedelta(hours=5, minutes=30))


@proof_router.get("/proof/nonce", summary="Get daily nonce for logged-in worker")
def get_worker_nonce(
    db: Session = Depends(get_db),
    worker_user: User = Depends(require_worker),
):
    worker = db.query(Worker).filter(Worker.user_id == worker_user.id).first()
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker profile not found",
        )

    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker.id, today_str)
    return {"date": today_str, "nonce": nonce}
