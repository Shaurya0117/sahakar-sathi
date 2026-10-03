from app.config import MAX_FATIGUE_THRESHOLD
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
WEIGHT_BIO_ECONOMIC= 0.10


def calculate_skill_score(service: Service, worker: Worker) -> float:
    s_name = (service.name or "").lower()
    s_cat = (service.category or "").lower()
    w_prof = (worker.profession or "").lower()
    w_skills = [s.lower() for s in (worker.skills or [])]

    score = 0.0

    if w_prof and (w_prof in s_name or w_prof in s_cat or s_name in w_prof):
        score += 70.0
    elif any(k in s_name for k in ["electric", "plumb", "clean", "carpent", "paint", "ac"]):
        score += 60.0
    else:
        score += 50.0

    service_words = set(re.sub(r"[^\w\s]", "", f"{s_name} {s_cat}").split())
    matching_skills = 0
    for skill in w_skills:
        skill_words = set(re.sub(r"[^\w\s]", "", skill).split())
        if skill_words.intersection(service_words) or any(w in s_name for w in skill_words):
            matching_skills += 1

    score += matching_skills * 10.0
    return min(100.0, max(0.0, score))


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
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
    return 100.0 if worker.availability == AvailabilityStatus.AVAILABLE else 0.0


def calculate_rating_score(worker: Worker) -> float:
    if not worker.rating or worker.rating <= 0:
        return 70.0 
    return min(100.0, max(0.0, (worker.rating / 5.0) * 100.0))


def calculate_experience_score(worker: Worker) -> float:
    exp = worker.experience_years or 0
    if exp == 0:
        return 30.0
    elif exp <= 2:
        return 60.0
    elif exp <= 4:
        return 80.0
    else:
        return 100.0


def calculate_bio_economic_metrics(worker: Worker, db: Session = None) -> dict:
    """
    Workload & Income Health Fatigue Routing Algorithm
    Merged into the Equity Index (Patent 3 & 4 combined).
    """
    from app.services.matching.equity_graph import calculate_fatigue_capacity, calculate_income_parity
    from app.database import SessionLocal
    
    session = db or SessionLocal()
    try:
        fatigue_capacity = calculate_fatigue_capacity(session, worker)
        fatigue_index = 100.0 - fatigue_capacity
        is_fatigued = fatigue_index >= 90.0 # capacity <= 10.0
        
        # We reuse the income parity score from equity index
        income_parity = calculate_income_parity(session, worker)
        economic_deficit = income_parity # Parity score is higher if deficit is higher
        
        workload_income_health_score = max(10.0, 100.0 - fatigue_index + economic_deficit) if not is_fatigued else 0.0
        
        return {
            "fatigue_index": round(fatigue_index, 1),
            "economic_deficit": round(economic_deficit, 1),
            "workload_income_health_score": min(100.0, round(workload_income_health_score, 1)),
            "is_fatigued": is_fatigued
        }
    finally:
        if not db:
            session.close()


def calculate_total_score(breakdown: dict) -> float:
    # Patent Feature: Use Equity Index composite score if available, fallback to legacy workload_income_health_score
    fairness_score = breakdown.get("equity_score") 
    if fairness_score is None:
        wf = breakdown.get("workload_fairness", {})
        if isinstance(wf, dict):
            fairness_score = wf.get("workload_income_health_score", 0.0)
        else:
            fairness_score = wf

    total = (
        breakdown.get("skill_match", 0)       * WEIGHT_SKILL +
        breakdown.get("location", 0)          * WEIGHT_LOCATION +
        breakdown.get("availability", 0)      * WEIGHT_AVAILABILITY +
        breakdown.get("rating", 0)            * WEIGHT_RATING +
        breakdown.get("experience", 0)        * WEIGHT_EXPERIENCE +
        fairness_score                        * WEIGHT_BIO_ECONOMIC
    )
    return round(min(100.0, max(0.0, total)), 1)

