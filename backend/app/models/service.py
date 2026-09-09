"""
Service catalog SQLAlchemy ORM model.

Foundation for service requests, marketplace categories, and worker skills.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float
from sqlalchemy.sql import func

from app.database.session import Base


class Service(Base):
    """
    Service catalog entry model.
    """

    __tablename__ = "services"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(128), nullable=False, unique=True, index=True)
    category: str = Column(String(128), nullable=False)
    description: Optional[str] = Column(String(512), nullable=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    
    # New fields for Urban Company style rich UI
    price: float = Column(Float, default=0.0, nullable=False) # Base price in INR or generic currency
    duration_minutes: int = Column(Integer, default=60, nullable=False) # Estimated duration
    image_url: Optional[str] = Column(String(256), nullable=True) # Rich image for the service card
    icon: Optional[str] = Column(String(64), nullable=True) # Emoji or icon class for sidebar
    rating: float = Column(Float, default=5.0, nullable=False) # Average rating
    reviews_count: int = Column(Integer, default=0, nullable=False) # Total reviews

    created_at: datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r} category={self.category!r}>"
