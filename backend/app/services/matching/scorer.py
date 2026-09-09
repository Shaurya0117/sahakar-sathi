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


def calculate_bio_economic_metrics(worker: Worker) -> dict:
    """
    Novel Patent Feature: Bio-Economic Fatigue Routing Algorithm
    Calculates physical strain and income parity.
    Includes a safety floor: if fatigue is too high, the worker is blocked.
    """
    jobs = worker.total_jobs or 0
    
    # Fatigue Index: scales non-linearly with jobs (mocking physiological strain over a period)
    # Higher index = more exhausted
    fatigue_index = min(100.0, jobs * 3.5)
    
    # Safety Floor Hard Cap (8/10 or 80.0)
    is_fatigued = fatigue_index >= 80.0
    
    # Economic Deficit: How far is the worker from the cooperative's target weekly parity income?
    target_income = 5000 
    actual_income = jobs * 500
    economic_deficit = max(0.0, min(100.0, ((target_income - actual_income) / target_income) * 100))
    
    # Bio-Economic Score: High deficit boosts score, High fatigue reduces score
    bio_economic_score = max(10.0, 100.0 - fatigue_index + economic_deficit) if not is_fatigued else 0.0
    
    return {
        "fatigue_index": round(fatigue_index, 1),
        "economic_deficit": round(economic_deficit, 1),
        "bio_economic_score": min(100.0, round(bio_economic_score, 1)),
        "is_fatigued": is_fatigued
    }


def calculate_total_score(breakdown: dict) -> float:
    total = (
        breakdown["skill_match"]       * WEIGHT_SKILL +
        breakdown["location"]          * WEIGHT_LOCATION +
        breakdown["availability"]      * WEIGHT_AVAILABILITY +
        breakdown["rating"]            * WEIGHT_RATING +
        breakdown["experience"]        * WEIGHT_EXPERIENCE +
        breakdown["bio_economic_score"] * WEIGHT_BIO_ECONOMIC
    )
    return round(min(100.0, max(0.0, total)), 1)
