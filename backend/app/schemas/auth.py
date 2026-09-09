"""Pydantic schemas for authentication (login request/response)."""
from pydantic import BaseModel

from app.schemas.user import UserResponse


class LoginResponse(BaseModel):
    """Response returned by POST /api/auth/login."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RegisterResponse(BaseModel):
    """Response returned by POST /api/auth/register."""

    message: str
    user: UserResponse
