"""
Pydantic schemas for ServiceRequest.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.service_request import RequestStatus


class ServiceRequestCreateRequest(BaseModel):
    """Payload for POST /api/requests (Customer creates request)."""

    service_id: int
    location: str = Field(..., min_length=2, max_length=255)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    preferred_date: str = Field(..., min_length=8, max_length=32)
    preferred_time: str = Field(..., min_length=2, max_length=32)
    description: str = Field(..., min_length=5, max_length=1000)

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Description must be at least 5 non-whitespace characters")
        return s

    @field_validator("location")
    @classmethod
    def location_not_empty(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 2:
            raise ValueError("Location must be at least 2 non-whitespace characters")
        return s


class ServiceRequestResponse(BaseModel):
    """Safe, enriched response representation of a ServiceRequest."""

    id: int
    customer_id: int
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None

    service_id: int
    service_name: str
    service_category: str

    cooperative_id: Optional[int] = None
    cooperative_name: Optional[str] = None

    description: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    preferred_date: str
    preferred_time: str

    status: RequestStatus
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceRequestCancelResponse(BaseModel):
    """Response returned after cancelling a request."""

    message: str
    request: ServiceRequestResponse
