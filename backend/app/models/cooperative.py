"""
Cooperative SQLAlchemy ORM model.

Represents a worker-owned labor cooperative entity.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class Cooperative(Base):
    """
    Labor cooperative model.
    """

    __tablename__ = "cooperatives"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(255), nullable=False)
    location: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(String(512), nullable=True)
    admin_id: Optional[int] = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    admin = relationship("User", foreign_keys=[admin_id], lazy="select")

    def __repr__(self) -> str:
        return f"<Cooperative id={self.id} name={self.name!r}>"
