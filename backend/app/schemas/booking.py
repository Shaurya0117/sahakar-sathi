"""
Pydantic validation schemas for Worker Allocation and Bookings.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AllocateWorkerRequest(BaseModel):
    """Payload sent by Cooperative Admin to allocate a worker to a service request."""

    worker_id: int = Field(..., description="ID of the verified worker to allocate")
    amount: Optional[float] = Field(None, description="Optional agreed service amount")

class ReviewCreateRequest(BaseModel):
    """Payload sent by Customer to review a completed booking."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    review: Optional[str] = Field(None, max_length=1000, description="Optional written review")


class BookingResponse(BaseModel):
    """Response representation of a Booking."""

    id: int
    request_id: int
    worker_id: int
    worker_name: str
    worker_phone: Optional[str] = None
    customer_id: int
    customer_name: str
    customer_phone: Optional[str] = None
    service_name: str
    service_category: str
    location: str
    scheduled_date: str
    scheduled_time: str
    status: str
    amount: Optional[float] = None
    image_url: Optional[str] = None
    customer_rating: Optional[int] = None
    customer_review: Optional[str] = None
    assigned_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
