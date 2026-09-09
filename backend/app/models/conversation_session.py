"""
ConversationSession ORM Model.

Stores multi-turn booking conversation states for WhatsApp and Voice/IVR channels.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="whatsapp")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW")
    context_data: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship to user
    customer = relationship("User")

    def __repr__(self) -> str:
        return f"<ConversationSession(id={self.id}, channel='{self.channel}', phone='{self.phone}', state='{self.state}')>"
