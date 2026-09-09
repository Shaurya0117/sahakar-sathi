"""
Scoring Engine for Worker Matching.

Calculates deterministic component scores (0–100) and weighted total score.

Weights:
    Skill Match       = 30%
    Distance/Location = 20%
    Availability       = 20%
    Rating             = 10%
    Experience         = 10%
    Workload Fairness  = 10%
"""
import math
import re
from typing import Optional
from app.models.service import Service
from app.models.worker import AvailabilityStatus, Worker

# Scoring Factor Weights (Total = 1.0)
WEIGHT_SKILL       = 0.30
WEIGHT_LOCATION    = 0.20
WEIGHT_AVAILABILITY = 0.20
WEIGHT_RATING      = 0.10
WEIGHT_EXPERIENCE  = 0.10
WEIGHT_FAIRNESS    = 0.10


def calculate_skill_score(service: Service, worker: Worker) -> float:
    """
    Calculate Skill Match score (0–100).

    Base score for profession relevance + bonus per matching skill tag.
    """
    s_name = (service.name or "").lower()
    s_cat = (service.category or "").lower()
    w_prof = (worker.profession or "").lower()
    w_skills = [s.lower() for s in (worker.skills or [])]

    score = 0.0

    # Direct profession relevance
    if w_prof and (w_prof in s_name or w_prof in s_cat or s_name in w_prof):
        score += 70.0
    elif any(k in s_name for k in ["electric", "plumb", "clean", "carpent", "paint", "ac"]):
        score += 60.0
    else:
        score += 50.0

    # Skill tag overlap bonus (+10 per skill up to max 100)
    service_words = set(re.sub(r"[^\w\s]", "", f"{s_name} {s_cat}").split())
    matching_skills = 0
    for skill in w_skills:
        skill_words = set(re.sub(r"[^\w\s]", "", skill).split())
        if skill_words.intersection(service_words) or any(w in s_name for w in skill_words):
            matching_skills += 1

    score += matching_skills * 10.0
    return min(100.0, max(0.0, score))


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points on the Earth.
    """
    R = 6371.0  # Earth radius in kilometers

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calculate_location_score(
    request_location: str,
    worker_location: str,
    request_lat: Optional[float] = None,
    request_lon: Optional[float] = None,
    worker_lat: Optional[float] = None,
    worker_lon: Optional[float] = None,
) -> float:
    """
    Calculate Location Compatibility score (0–100).

    Geographic distance (Haversine) when coordinates are available:
        0–2 km   = 100.0
        2–5 km   = 90.0
        5–10 km  = 75.0
        10–20 km = 55.0
        20+ km   = 30.0

    Fallback to string locality matching when coordinates are absent:
        Exact locality match = 100.0
        Same sub-locality / sector = 85.0
        Same city/region = 75.0
        Different locality = 40.0
        Unspecified = 50.0
    """
    # 1. Geographic distance check if both coordinate pairs are available
    if (
        request_lat is not None and request_lon is not None and
        worker_lat is not None and worker_lon is not None
    ):
        dist_km = calculate_haversine_distance(request_lat, request_lon, worker_lat, worker_lon)
        if dist_km <= 2.0:
            return 100.0
        elif dist_km <= 5.0:
            return 90.0
        elif dist_km <= 10.0:
            return 75.0
        elif dist_km <= 20.0:
            return 55.0
        else:
            return 30.0

    # 2. String locality fallback matching
    if not request_location or not worker_location:
        return 50.0

    r_clean = re.sub(r"[^\w\s]", "", request_location.lower()).strip()
    w_clean = re.sub(r"[^\w\s]", "", worker_location.lower()).strip()

    if r_clean == w_clean:
        return 100.0

    r_tokens = set(r_clean.split())
    w_tokens = set(w_clean.split())

    overlap = r_tokens.intersection(w_tokens)
    if len(overlap) >= 2:
        return 90.0
    elif len(overlap) == 1 and not (overlap.issubset({"in", "at", "near", "sector"})):
        return 80.0
    elif any(city in r_clean and city in w_clean for city in ["noida", "ghaziabad", "delhi", "ncr"]):
        return 75.0

    return 40.0


def calculate_availability_score(worker: Worker) -> float:
    """
    Calculate Availability score (0–100).
    AVAILABLE = 100.0, UNAVAILABLE = 0.0.
    """
    return 100.0 if worker.availability == AvailabilityStatus.AVAILABLE else 0.0


def calculate_rating_score(worker: Worker) -> float:
    """
    Calculate Rating score (0–100).

    Normalize 0–5 stars into 0–100.
    Unrated workers receive neutral score (70.0) to prevent unfair penalty.
    """
    if not worker.rating or worker.rating <= 0:
        return 70.0  # Neutral default for new workers

    return min(100.0, max(0.0, (worker.rating / 5.0) * 100.0))


def calculate_experience_score(worker: Worker) -> float:
    """
    Calculate Experience score (0–100).

    Normalize experience_years:
        0 years = 30.0
        1–2 years = 60.0
        3–4 years = 80.0
        5+ years = 100.0 (capped at 100.0)
    """
    exp = worker.experience_years or 0
    if exp == 0:
        return 30.0
    elif exp <= 2:
        return 60.0
    elif exp <= 4:
        return 80.0
    else:
        return 100.0


def calculate_fairness_score(worker: Worker) -> float:
    """
    Calculate Workload Fairness score (0–100).

    Cooperative principle: lower current workload (total_jobs) produces
    a HIGHER fairness score, giving work opportunities to newer or lower-workload members.

    Formula: max(30.0, 100.0 - (total_jobs * 2.5))
        total_jobs = 0  -> 100.0
        total_jobs = 4  -> 90.0
        total_jobs = 15 -> 62.5
        total_jobs = 28+ -> 30.0
    """
    jobs = worker.total_jobs or 0
    return max(30.0, 100.0 - (jobs * 2.5))


def calculate_total_score(breakdown: dict) -> float:
    """
    Calculate weighted total score (0–100), rounded to 1 decimal place.
    """
    total = (
        breakdown["skill_match"]       * WEIGHT_SKILL +
        breakdown["location"]          * WEIGHT_LOCATION +
        breakdown["availability"]      * WEIGHT_AVAILABILITY +
        breakdown["rating"]            * WEIGHT_RATING +
        breakdown["experience"]        * WEIGHT_EXPERIENCE +
        breakdown["workload_fairness"] * WEIGHT_FAIRNESS
    )
    return round(min(100.0, max(0.0, total)), 1)
