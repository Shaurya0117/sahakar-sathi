"""
Pydantic schemas for Explainable AI Worker Matching.
"""
from typing import List, Optional

from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    """Component scores (0–100) for each factor."""

    skill_match: float
    location: float
    availability: float
    rating: float
    experience: float
    workload_fairness: float


class WorkerRecommendation(BaseModel):
    """Ranked worker recommendation entry with score breakdown & human-readable reasons."""

    worker_id: int
    worker_name: str
    profession: Optional[str] = None
    verification_status: str
    rating: float
    experience_years: Optional[int] = 0
    location: Optional[str] = None
    total_jobs: int
    score: float
    breakdown: ScoreBreakdown
    reasons: List[str]


class RequestMatchingResponse(BaseModel):
    """Response returned by GET /api/matching/requests/{request_id}."""

    request_id: int
    service_name: str
    service_category: str
    request_location: str
    candidate_count: int
    recommendations: List[WorkerRecommendation]
