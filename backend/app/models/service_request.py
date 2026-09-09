"""
ServiceRequest SQLAlchemy ORM model.

Represents a customer's request for a cooperative household/community service.
"""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class RequestStatus(str, enum.Enum):
    """Lifecycle status of a service request."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ServiceRequest(Base):
    """
    Customer service request model.
    """

    __tablename__ = "service_requests"

    id: int = Column(Integer, primary_key=True, index=True)
    customer_id: int = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_id: int = Column(
        Integer, ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    cooperative_id: int = Column(
        Integer, ForeignKey("cooperatives.id", ondelete="SET NULL"), nullable=True, index=True
    )

    description: str = Column(Text, nullable=False)
    location: str = Column(String(255), nullable=False)
    latitude: float = Column(Float, nullable=True)
    longitude: float = Column(Float, nullable=True)
    preferred_date: str = Column(String(32), nullable=False)
    preferred_time: str = Column(String(32), nullable=False)
    image_url: str = Column(String(512), nullable=True)

    status: RequestStatus = Column(
        Enum(RequestStatus, name="requeststatus"),
        nullable=False,
        default=RequestStatus.PENDING,
        index=True,
    )

    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer = relationship("User", foreign_keys=[customer_id], lazy="select")
    service = relationship("Service", foreign_keys=[service_id], lazy="select")
    cooperative = relationship("Cooperative", foreign_keys=[cooperative_id], lazy="select")

    def __repr__(self) -> str:
        return (
            f"<ServiceRequest id={self.id} customer_id={self.customer_id} "
            f"service_id={self.service_id} status={self.status}>"
        )
