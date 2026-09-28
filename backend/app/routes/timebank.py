from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.dependencies import require_worker
from app.models.worker import Worker
from app.services.timebank import transfer_credits, get_transaction_history

router = APIRouter(prefix="/timebank", tags=["Time Bank"])

class TransferRequest(BaseModel):
    receiver_id: int
    amount: float
    description: str

@router.post("/transfer")
def api_transfer_credits(body: TransferRequest, user=Depends(require_worker), db: Session = Depends(get_db)):
    sender = db.query(Worker).filter(Worker.user_id == user.id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
        
    try:
        return transfer_credits(db, sender, body.receiver_id, body.amount, body.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history")
def api_get_history(user=Depends(require_worker), db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.user_id == user.id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
        
    return {
        "balance": worker.time_credits or 0,
        "history": get_transaction_history(db, worker.id)
    }
