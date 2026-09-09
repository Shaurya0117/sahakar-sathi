"""
Explainable Cooperative Worker Matching Module.
"""
from app.services.matching.candidate_filter import filter_eligible_candidates
from app.services.matching.engine import get_matching_recommendations
from app.services.matching.explain import generate_match_explanation
from app.services.matching.scorer import (
    WEIGHT_AVAILABILITY,
    WEIGHT_EXPERIENCE,
    WEIGHT_BIO_ECONOMIC,
    WEIGHT_LOCATION,
    WEIGHT_RATING,
    WEIGHT_SKILL,
    calculate_availability_score,
    calculate_experience_score,
    calculate_bio_economic_metrics,
    calculate_location_score,
    calculate_rating_score,
    calculate_skill_score,
    calculate_total_score,
)

__all__ = [
    "get_matching_recommendations",
    "filter_eligible_candidates",
    "calculate_skill_score",
    "calculate_location_score",
    "calculate_availability_score",
    "calculate_rating_score",
    "calculate_experience_score",
    "calculate_bio_economic_metrics",
    "calculate_total_score",
    "generate_match_explanation",
    "WEIGHT_SKILL",
    "WEIGHT_LOCATION",
    "WEIGHT_AVAILABILITY",
    "WEIGHT_RATING",
    "WEIGHT_EXPERIENCE",
    "WEIGHT_BIO_ECONOMIC",
]
