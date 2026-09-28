"""
Cooperative Time Banking — Backend Service

Time Bank model logs all time credit transactions (earning and transferring).
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from app.database.session import Base

class TimeBankTransaction(Base):
    __tablename__ = "timebank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("workers.id"), nullable=True) # Null = Co-op system
    receiver_id = Column(Integer, ForeignKey("workers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
