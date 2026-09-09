"""
Pydantic schemas for Cooperative and Admin statistics.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CooperativeResponse(BaseModel):
    """Details of the primary cooperative."""

    id: int
    name: str
    location: str
    description: Optional[str] = None
    admin_id: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CooperativeStatsResponse(BaseModel):
    """
    Lightweight workforce and operational statistics calculated directly from the DB.
    """

    total_workers: int
    verified_workers: int
    pending_workers: int
    rejected_workers: int
    available_workers: int
    unavailable_workers: int

from typing import List, Dict, Any

class AnalyticsResponse(BaseModel):
    jobs_by_status: Dict[str, int]
    jobs_by_category: Dict[str, int]
    recent_jobs_trend: List[Dict[str, Any]]
