"""
Booking SQLAlchemy ORM model and BookingStatus Enum.
"""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.session import Base


class BookingStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Booking(Base):
    """
    Represents an allocated service job connecting a ServiceRequest to a Worker.
    Managed by the Cooperative Admin.
    """
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("service_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    status = Column(Enum(BookingStatus), default=BookingStatus.ASSIGNED, nullable=False, index=True)
    amount = Column(Float, nullable=True)
    scheduled_date = Column(String(32), nullable=False)
    scheduled_time = Column(String(32), nullable=False)
    customer_rating = Column(Integer, nullable=True) # 1 to 5
    customer_review = Column(String(1000), nullable=True)
    payment_status = Column(String(50), default="PENDING")
    
    # Novel Patent Feature: Privacy-Preserving Proof of Work (Edge AI)
    proof_of_work_hash = Column(String(255), nullable=True)
    privacy_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    service_request = relationship("ServiceRequest", backref="bookings")
    worker = relationship("Worker", backref="bookings")
    assigner = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self):
        return f"<Booking id={self.id} request_id={self.request_id} worker_id={self.worker_id} status={self.status}>"
