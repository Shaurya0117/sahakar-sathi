"""
Pydantic schemas for Service catalog.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ServiceCreateRequest(BaseModel):
    """Payload for creating a service in the catalog."""

    name: str = Field(..., min_length=2, max_length=128)
    category: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    is_active: bool = True
    
    price: float = 0.0
    duration_minutes: int = 60
    image_url: Optional[str] = None
    icon: Optional[str] = None
    rating: float = 5.0
    reviews_count: int = 0


class ServiceResponse(BaseModel):
    """Response representation of a Service catalog item."""

    id: int
    name: str
    category: str
    description: Optional[str] = None
    is_active: bool
    price: float
    duration_minutes: int
    image_url: Optional[str] = None
    icon: Optional[str] = None
    rating: float
    reviews_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
