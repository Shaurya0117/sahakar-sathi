"""
Worker SQLAlchemy ORM model.

One-to-one relationship with User:
    Worker.user_id → users.id (unique)

Skills are stored as JSON (a list of strings) for hackathon speed.
This allows a later migration to a normalized Skill table without changing
the API response shape.
"""
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class VerificationStatus(str, enum.Enum):
    """Admin-controlled verification lifecycle."""
    PENDING  = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class AvailabilityStatus(str, enum.Enum):
    """Worker's self-declared availability."""
    AVAILABLE   = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"


# SQLite does not have a native JSON column but SQLAlchemy's JSON type
# maps to TEXT on SQLite and serialises/deserialises transparently.
try:
    from sqlalchemy import JSON
    _JSON = JSON
except ImportError:
    from sqlalchemy import Text as _JSON  # type: ignore


class Worker(Base):
    """
    Professional profile for a WORKER-role user.

    - Created by the worker themselves after registration.
    - Verification is controlled exclusively by ADMIN.
    - rating and total_jobs are updated by the booking/rating system in a future
      mission; workers cannot edit them directly.
    """

    __tablename__ = "workers"
    __table_args__ = (
        # Enforce the one-to-one constraint at the DB level
        UniqueConstraint("user_id", name="uq_workers_user_id"),
    )

    id: int              = Column(Integer, primary_key=True, index=True)
    user_id: int         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Optional cooperative membership (linked to primary demo cooperative)
    cooperative_id: Optional[int] = Column(Integer, ForeignKey("cooperatives.id", ondelete="SET NULL"), nullable=True)

    # Professional information
    profession: Optional[str]  = Column(String(128), nullable=True)
    experience_years: Optional[int] = Column(Integer, nullable=True)  # 0–60
    location: Optional[str]    = Column(String(255), nullable=True)
    latitude: Optional[float]  = Column(Float, nullable=True)
    longitude: Optional[float] = Column(Float, nullable=True)

    # Skills stored as a JSON list of strings — e.g. ["Wiring", "Fan Repair"]
    # SQLAlchemy's JSON type handles serialisation transparently on SQLite.
    skills = Column(_JSON, nullable=True, default=list)

    # Simple availability flag + optional human-readable schedule description
    availability: AvailabilityStatus = Column(
        Enum(AvailabilityStatus, name="availabilitystatus"),
        nullable=False,
        default=AvailabilityStatus.AVAILABLE,
    )
    availability_description: Optional[str] = Column(String(255), nullable=True)

    # Admin-controlled — workers can NEVER change these via the worker API
    verification_status: VerificationStatus = Column(
        Enum(VerificationStatus, name="verificationstatus"),
        nullable=False,
        default=VerificationStatus.PENDING,
    )

    # Populated by the rating system in a later mission
    rating: float    = Column(Float, nullable=False, default=0.0)
    total_jobs: int  = Column(Integer, nullable=False, default=0)

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

    # Relationship — allows worker.user to access User object
    user = relationship("User", back_populates="worker_profile", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<Worker id={self.id} user_id={self.user_id} "
            f"profession={self.profession!r} status={self.verification_status}>"
        )
