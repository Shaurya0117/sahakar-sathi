from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.auth.dependencies import require_worker
from app.models.worker import Worker
from app.services.india_stack import verify_eshram_uan

router = APIRouter(prefix="/india-stack", tags=["India Stack Integration"])

class VerifyUANRequest(BaseModel):
    uan_number: str

@router.post("/verify-eshram")
def verify_eshram(body: VerifyUANRequest, user=Depends(require_worker), db: Session = Depends(get_db)):
    """Mock verify a worker via e-Shram and DigiLocker."""
    worker = db.query(Worker).filter(Worker.user_id == user.id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker profile not found.")
        
    try:
        return verify_eshram_uan(db, worker, body.uan_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
