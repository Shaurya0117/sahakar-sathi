"""
Micro-Credit API Routes

Endpoints:
  GET  /api/microcredit/eligibility  — Check loan eligibility (WORKER)
  POST /api/microcredit/apply        — Apply for micro-loan (WORKER)
  GET  /api/microcredit/my-loans     — List my loans (WORKER)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.dependencies import require_worker
from app.models.worker import Worker
from app.services.microcredit import check_eligibility, apply_for_loan, get_my_loans

router = APIRouter(prefix="/microcredit", tags=["Micro-Credit"])


class LoanApplication(BaseModel):
    amount: float
    purpose: str = "Salary Advance"


@router.get("/eligibility")
def get_eligibility(user=Depends(require_worker), db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.user_id == user.id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
    return check_eligibility(db, worker)


@router.post("/apply")
def apply_loan(body: LoanApplication, user=Depends(require_worker), db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.user_id == user.id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
    try:
        return apply_for_loan(db, worker, body.amount, body.purpose)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-loans")
def my_loans(user=Depends(require_worker), db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.user_id == user.id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
    return get_my_loans(db, worker.id)
