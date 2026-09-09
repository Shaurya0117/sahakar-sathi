"""
User SQLAlchemy ORM model.
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class UserRole(str, enum.Enum):
    """Roles available on the platform."""
    CUSTOMER = "CUSTOMER"
    WORKER = "WORKER"
    ADMIN = "ADMIN"


class User(Base):
    """Platform user — common to all three roles."""

    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(128), nullable=False)
    email: str = Column(String(255), unique=True, index=True, nullable=False)
    phone: str = Column(String(20), nullable=True)
    password_hash: str = Column(String(255), nullable=False)
    role: UserRole = Column(
        Enum(UserRole, name="userrole"),
        nullable=False,
        default=UserRole.CUSTOMER,
    )
    is_active: bool = Column(Boolean, default=True, nullable=False)
    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship — allows user.worker_profile to access Worker object
    worker_profile = relationship(
        "Worker", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
