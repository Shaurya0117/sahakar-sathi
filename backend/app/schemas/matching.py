"""
Pydantic schemas for Explainable AI Worker Matching.

Includes Patent Feature: Cooperative Workload Equity Index — multi-dimensional
fairness scoring across income parity, geographic burden, skill utilization,
temporal equity, and fatigue capacity.
"""
from typing import Dict, List, Optional

from pydantic import BaseModel


class EquityDimensionContributions(BaseModel):
    """Weighted contribution of each equity dimension to the composite score."""

    income_parity: float = 0.0
    geographic_burden: float = 0.0
    skill_utilization: float = 0.0
    temporal_fairness: float = 0.0
    fatigue_capacity: float = 0.0


class EquityBreakdown(BaseModel):
    """
    Patent Feature: Cooperative Workload Equity Index.

    Multi-dimensional fairness breakdown for a worker candidate,
    computed in real-time during matching.
    """

    income_parity: float = 0.0
    geographic_burden: float = 0.0
    skill_utilization: float = 0.0
    temporal_fairness: float = 0.0
    fatigue_capacity: float = 0.0
    composite_equity_score: float = 0.0
    is_fatigued: bool = False
    dimension_contributions: Optional[EquityDimensionContributions] = None


class ScoreBreakdown(BaseModel):
    """Component scores (0–100) for each factor."""

    skill_match: float
    location: float
    availability: float
    rating: float
    experience: float
    workload_income_health_score: float
    fatigue_index: float
    economic_deficit: float
    # Patent Feature: Equity Index dimensions
    equity: Optional[EquityBreakdown] = None


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
    # Patent Feature: Trust Score (populated when available)
    trust_score: Optional[float] = None
    ml_accept_probability: Optional[float] = None
    ml_used: bool = False


class RequestMatchingResponse(BaseModel):
    """Response returned by GET /api/matching/requests/{request_id}."""

    request_id: int
    service_name: str
    service_category: str
    request_location: str
    candidate_count: int
    recommendations: List[WorkerRecommendation]
    ml_used: bool = False
