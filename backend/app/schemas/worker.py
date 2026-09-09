"""
Pydantic schemas for the Worker profile.

Separation of concerns:
    WorkerCreateRequest  — POST /api/workers/me  (worker creates their own profile)
    WorkerUpdateRequest  — PUT /api/workers/me   (worker edits their own profile)
    WorkerResponse       — all responses, includes computed fields
    VerificationUpdateRequest — PATCH /api/workers/{id}/verification  (admin only)

PROTECTED FIELDS — never accepted from worker update requests:
    verification_status, rating, total_jobs
These are server-controlled and enforced at the service layer.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.worker import AvailabilityStatus, VerificationStatus


# ── Request: Worker creates their own profile ──────────────────────────────────

class WorkerCreateRequest(BaseModel):
    """Payload for POST /api/workers/me."""

    profession: str = Field(..., min_length=2, max_length=128)
    skills: List[str] = Field(default_factory=list)
    experience_years: int = Field(..., ge=0, le=60)
    location: Optional[str] = Field(None, min_length=2, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    availability: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    availability_description: Optional[str] = Field(None, max_length=255)

    @field_validator("skills")
    @classmethod
    def skills_are_strings(cls, v: List[str]) -> List[str]:
        """Ensure each skill is a non-empty string after stripping."""
        cleaned = [s.strip() for s in v if s.strip()]
        return cleaned


# ── Request: Worker edits their own profile ────────────────────────────────────

class WorkerUpdateRequest(BaseModel):
    """Payload for PUT /api/workers/me.

    All fields are optional — send only what you want to change.
    Protected fields (verification_status, rating, total_jobs) are absent by design.
    """

    profession: Optional[str] = Field(None, min_length=2, max_length=128)
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0, le=60)
    location: Optional[str] = Field(None, min_length=2, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    availability: Optional[AvailabilityStatus] = None
    availability_description: Optional[str] = Field(None, max_length=255)

    @field_validator("skills")
    @classmethod
    def skills_are_strings(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        return [s.strip() for s in v if s.strip()]


# ── Response: Worker profile (enriched with User fields) ──────────────────────

class WorkerResponse(BaseModel):
    """
    Safe, enriched worker profile response.

    - name / email come from the joined User record.
    - profile_completion is calculated server-side.
    - password / password_hash are never included.
    """

    id: int
    user_id: int

    # Flattened from User
    name: str
    email: str
    phone: Optional[str] = None

    # Worker professional info
    profession: Optional[str] = None
    skills: List[str] = []
    experience_years: Optional[int] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    availability: AvailabilityStatus
    availability_description: Optional[str] = None

    # Admin-controlled
    verification_status: VerificationStatus

    # System-managed
    rating: float
    total_jobs: int

    # Computed server-side
    profile_completion: int  # percentage 0–100

    model_config = {"from_attributes": True}


# ── Request: Admin updates verification status ─────────────────────────────────

class VerificationUpdateRequest(BaseModel):
    """Payload for PATCH /api/workers/{id}/verification (ADMIN only)."""

    status: VerificationStatus
