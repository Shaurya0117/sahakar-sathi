"""
Time Banking Logic
"""
from sqlalchemy.orm import Session
from app.models.worker import Worker
from app.models.timebank import TimeBankTransaction

def award_time_credit(db: Session, worker_id: int, amount: float, description: str):
    """System awards time credits to a worker (e.g. for completing a job)."""
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        return
    
    worker.time_credits = (worker.time_credits or 0) + amount
    
    txn = TimeBankTransaction(
        sender_id=None,
        receiver_id=worker.id,
        amount=amount,
        description=description
    )
    db.add(txn)
    db.commit()

def transfer_credits(db: Session, sender: Worker, receiver_id: int, amount: float, description: str):
    """Worker transfers time credits to another worker."""
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
        
    if sender.id == receiver_id:
        raise ValueError("Cannot transfer credits to yourself.")
        
    if (sender.time_credits or 0) < amount:
        raise ValueError("Insufficient time credits.")
        
    receiver = db.query(Worker).filter(Worker.id == receiver_id).first()
    if not receiver:
        raise ValueError("Receiver not found.")
        
    sender.time_credits -= amount
    receiver.time_credits = (receiver.time_credits or 0) + amount
    
    txn = TimeBankTransaction(
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=amount,
        description=description
    )
    db.add(txn)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Successfully transferred {amount} credits to Worker #{receiver.id}.",
        "new_balance": sender.time_credits
    }

def get_transaction_history(db: Session, worker_id: int):
    txns = db.query(TimeBankTransaction).filter(
        (TimeBankTransaction.sender_id == worker_id) | (TimeBankTransaction.receiver_id == worker_id)
    ).order_by(TimeBankTransaction.timestamp.desc()).all()
    
    history = []
    for t in txns:
        is_credit = t.receiver_id == worker_id
        history.append({
            "id": t.id,
            "type": "EARNED" if is_credit and t.sender_id is None else ("RECEIVED" if is_credit else "SENT"),
            "amount": t.amount,
            "description": t.description,
            "timestamp": t.timestamp.isoformat(),
            "counterparty": t.sender_id if is_credit else t.receiver_id
        })
    return history
