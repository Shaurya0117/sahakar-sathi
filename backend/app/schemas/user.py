"""Pydantic schemas for User (request & response)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole


# ── Request schemas ────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    """Payload accepted by POST /api/auth/register."""

    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: UserRole = UserRole.CUSTOMER

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("role")
    @classmethod
    def role_not_admin(cls, v: UserRole) -> UserRole:
        """
        Prevent self-registration as ADMIN.
        Admins are seeded via the seed_admin script.
        """
        if v == UserRole.ADMIN:
            raise ValueError("Cannot self-register as ADMIN")
        return v


# ── Response schemas ───────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Safe user representation — NEVER includes password_hash."""

    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
