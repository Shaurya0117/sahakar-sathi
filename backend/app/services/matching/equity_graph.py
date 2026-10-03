from app.config import MAX_FATIGUE_THRESHOLD
"""
Patent Feature: Cooperative Workload Equity Index.

A Multi-Dimensional Fairness Optimization System for Cooperative Gig Platforms.

Unlike traditional gig platforms that optimize purely for individual match quality,
this algorithm simultaneously optimizes across 5 equity dimensions to ensure
cooperative-wide fairness in work distribution.

Equity Dimensions:
    1. Income Parity       (25%) — Fair-share earnings gap
    2. Geographic Burden   (20%) — Travel distance equity
    3. Skill Utilization   (20%) — Are high-skill workers underutilized?
    4. Temporal Fairness   (15%) — Time-slot distribution equity
    5. Fatigue Capacity    (20%) — Physical job intensity × recent load

Novel Claim:
    "A method for equitable work distribution in cooperative gig platforms using
    a multi-dimensional fairness tensor that simultaneously optimizes income parity,
    geographic burden, skill utilization, temporal equity, and physiological capacity
    across all cooperative members."
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.worker import Worker

# ── Job Physical Intensity Weights ────────────────────────────────────────────
# Maps service category keywords to a physical intensity factor (0.0 – 1.0).
# Higher = more physically demanding.
JOB_INTENSITY_MAP = {
    "plumb": 0.85,
    "electric": 0.70,
    "carpent": 0.80,
    "paint": 0.75,
    "clean": 0.60,
    "ac": 0.65,
    "repair": 0.70,
    "general": 0.50,
}

# ── Equity Dimension Weights (Total = 1.0) ───────────────────────────────────
WEIGHT_INCOME_PARITY     = 0.25
WEIGHT_GEOGRAPHIC_BURDEN = 0.20
WEIGHT_SKILL_UTILIZATION = 0.20
WEIGHT_TEMPORAL_FAIRNESS = 0.15
WEIGHT_FATIGUE_CAPACITY  = 0.20

# ── Cooperative Weekly Target Income (configurable) ──────────────────────────
COOPERATIVE_WEEKLY_TARGET = 5000.0  # ₹5000 per worker per week target


def _get_worker_recent_bookings(db: Session, worker_id: int, limit: int = 20) -> List[Booking]:
    """Fetch the most recent bookings for a worker (completed + in-progress)."""
    return (
        db.query(Booking)
        .filter(
            Booking.worker_id == worker_id,
            Booking.status.in_([
                BookingStatus.COMPLETED,
                BookingStatus.IN_PROGRESS,
                BookingStatus.ACCEPTED,
                BookingStatus.ASSIGNED,
            ]),
        )
        .order_by(Booking.created_at.desc())
        .limit(limit)
        .all()
    )


def calculate_income_parity(db: Session, worker: Worker) -> float:
    """
    Income Parity Score (0–100).

    Measures how far the worker's recent earnings are from the cooperative's
    target weekly income. Workers who have earned less get a HIGHER score
    (they should be prioritized for the next job).

    Formula: score = max(10, (target - actual) / target * 100)
    - Worker earned ₹0 this period   → score = 100 (maximum priority)
    - Worker earned target already    → score = 10  (minimum priority)
    - Worker earned more than target  → score = 10  (already well-served)
    """
    recent_bookings = _get_worker_recent_bookings(db, worker.id, limit=10)
    total_earnings = sum(b.amount or 0 for b in recent_bookings if b.status == BookingStatus.COMPLETED)

    if COOPERATIVE_WEEKLY_TARGET <= 0:
        return 50.0

    deficit_ratio = (COOPERATIVE_WEEKLY_TARGET - total_earnings) / COOPERATIVE_WEEKLY_TARGET
    score = max(10.0, min(100.0, deficit_ratio * 100.0))
    return round(score, 1)


def calculate_geographic_burden(db: Session, worker: Worker) -> float:
    """
    Geographic Burden Score (0–100).

    Analyzes the average distance the worker has been sent for recent jobs.
    Workers who have been consistently sent far away get a HIGHER score
    (they should be given nearby jobs next).

    Uses locality string matching as a proxy when GPS coordinates are unavailable.
    """
    recent_bookings = _get_worker_recent_bookings(db, worker.id, limit=10)

    if not recent_bookings:
        return 70.0  # Neutral — no history

    location_mismatches = 0
    total_checked = 0
    worker_loc = (worker.location or "").lower().strip()

    for booking in recent_bookings:
        req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
        if req and req.location:
            total_checked += 1
            req_loc = req.location.lower().strip()

            # Check if locations share tokens (rough proximity proxy)
            worker_tokens = set(worker_loc.split()) if worker_loc else set()
            req_tokens = set(req_loc.split()) if req_loc else set()

            # Filter out common stop words
            stop_words = {"in", "at", "near", "the", "of", "sector", "block"}
            worker_tokens -= stop_words
            req_tokens -= stop_words

            overlap = worker_tokens.intersection(req_tokens)
            if len(overlap) == 0 and worker_tokens and req_tokens:
                location_mismatches += 1

    if total_checked == 0:
        return 70.0

    # High mismatch ratio = worker has been sent far repeatedly = give higher equity score
    mismatch_ratio = location_mismatches / total_checked
    score = max(10.0, min(100.0, 50.0 + mismatch_ratio * 50.0))
    return round(score, 1)


def calculate_skill_utilization(db: Session, worker: Worker) -> float:
    """
    Skill Utilization Score (0–100).

    Measures whether a worker with broad skills is being underutilized
    on simple, repetitive jobs. A worker with 5 skills who has only been
    assigned to 1 service category is underutilized.

    Underutilized workers get HIGHER scores (prioritize diverse assignments).
    """
    worker_skills = worker.skills or []
    skill_breadth = len(worker_skills)

    if skill_breadth <= 1:
        return 50.0  # Single-skill worker — neutral

    recent_bookings = _get_worker_recent_bookings(db, worker.id, limit=15)

    if not recent_bookings:
        return 70.0  # No history — slight priority

    # Count distinct service categories in recent jobs
    service_ids = set()
    for booking in recent_bookings:
        req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
        if req:
            service_ids.add(req.service_id)

    categories_used = len(service_ids)
    utilization_ratio = categories_used / max(skill_breadth, 1)

    # Low utilization = high equity score (worker needs diverse work)
    score = max(10.0, min(100.0, (1.0 - utilization_ratio) * 80.0 + 20.0))
    return round(score, 1)


def calculate_temporal_fairness(db: Session, worker: Worker) -> float:
    """
    Temporal Fairness Score (0–100).

    Analyzes the distribution of assigned time slots. Workers who consistently
    get undesirable slots (very early or very late) receive HIGHER scores
    to be prioritized for better time slots.

    Undesirable hours: before 8 AM or after 6 PM.
    """
    recent_bookings = _get_worker_recent_bookings(db, worker.id, limit=10)

    if not recent_bookings:
        return 60.0  # Neutral

    undesirable_count = 0
    total_with_time = 0

    for booking in recent_bookings:
        scheduled_time = booking.scheduled_time or ""
        try:
            # Parse "HH:MM" format
            parts = scheduled_time.split(":")
            if len(parts) >= 1:
                hour = int(parts[0])
                total_with_time += 1
                if hour < 8 or hour >= 18:
                    undesirable_count += 1
        except (ValueError, IndexError):
            continue

    if total_with_time == 0:
        return 60.0

    undesirable_ratio = undesirable_count / total_with_time
    # High undesirable ratio = worker has been given bad slots = higher equity score
    score = max(10.0, min(100.0, 40.0 + undesirable_ratio * 60.0))
    return round(score, 1)


def _get_job_intensity(service_name: str, service_category: str) -> float:
    """Map a service to its physical intensity weight."""
    combined = f"{service_name} {service_category}".lower()
    for keyword, intensity in JOB_INTENSITY_MAP.items():
        if keyword in combined:
            return intensity
    return 0.50  # Default moderate intensity


def calculate_fatigue_capacity(db: Session, worker: Worker) -> float:
    """
    Fatigue Capacity Score (0–100).

    Models physical strain as a function of recent job count weighted by
    job physical intensity, duration, and a time-decay factor (0.8^days_ago) over 7 days.
    
    Formula: load = Σ (intensity × hours × 0.8^days_ago)
    fatigue = min(100, load / safe_load × 100)
    capacity = 100 - fatigue
    """
    from datetime import datetime, timezone
    
    # Fetch all bookings from the last 7 days
    recent_bookings = _get_worker_recent_bookings(db, worker.id, limit=50)

    if not recent_bookings:
        return 90.0  # Fresh worker — high capacity

    load = 0.0
    now = datetime.now(timezone.utc)
    
    for booking in recent_bookings:
        # Check if booking is within last 7 days
        days_ago = 0
        if booking.updated_at:
            # Assumes updated_at is naive or aware, making it naive for timedelta if needed
            booking_time = booking.updated_at
            if booking_time.tzinfo is None:
                # If naive, compare with naive utcnow
                delta = datetime.utcnow() - booking_time
            else:
                delta = now - booking_time
            days_ago = delta.total_seconds() / (24 * 3600)
            
        if days_ago > 7:
            continue

        req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
        hours = 1.0 # Default 1 hour
        intensity = 0.50
        
        if req:
            service = db.query(Service).filter(Service.id == req.service_id).first()
            if service:
                intensity = _get_job_intensity(service.name, service.category)
                hours = (service.duration_minutes or 60) / 60.0

        status_multiplier = 1.0
        if booking.status in (BookingStatus.IN_PROGRESS, BookingStatus.ACCEPTED):
            status_multiplier = 0.5  # Upcoming jobs contribute partial fatigue
            days_ago = 0 # Currently happening
        elif booking.status != BookingStatus.COMPLETED:
            continue

        job_load = intensity * hours * (0.8 ** max(0, days_ago)) * status_multiplier
        load += job_load

    # Assuming a safe_load of around 15-20 (e.g. 5 days of 4 hours at 0.8 intensity = 16)
    safe_load = 18.0
    fatigue_index = min(100.0, (load / safe_load) * 100.0)
    capacity_score = max(0.0, 100.0 - fatigue_index)

    return round(capacity_score, 1)


def is_worker_fatigued(db: Session, worker: Worker) -> bool:
    """
    Safety Floor Check.
    Returns True if the worker's fatigue exceeds the safety threshold.
    Fatigued workers should be excluded from recommendations entirely.
    """
    capacity = calculate_fatigue_capacity(db, worker)
    return capacity <= (100 - MAX_FATIGUE_THRESHOLD)  # Exceeds max fatigue


def calculate_equity_score(db: Session, worker: Worker) -> Dict:
    """
    Master Equity Index Computation.

    Computes all 5 equity dimensions and returns a comprehensive breakdown
    with per-dimension scores, weights, and composite equity score.

    Returns:
        dict with keys:
            - income_parity: float (0-100)
            - geographic_burden: float (0-100)
            - skill_utilization: float (0-100)
            - temporal_fairness: float (0-100)
            - fatigue_capacity: float (0-100)
            - composite_equity_score: float (0-100)
            - is_fatigued: bool
            - dimension_contributions: dict (per-dimension weighted contribution)
    """
    income = calculate_income_parity(db, worker)
    geographic = calculate_geographic_burden(db, worker)
    skill = calculate_skill_utilization(db, worker)
    temporal = calculate_temporal_fairness(db, worker)
    fatigue = calculate_fatigue_capacity(db, worker)

    is_fatigued = fatigue <= (100 - MAX_FATIGUE_THRESHOLD)

    # Weighted composite
    composite = (
        income     * WEIGHT_INCOME_PARITY +
        geographic * WEIGHT_GEOGRAPHIC_BURDEN +
        skill      * WEIGHT_SKILL_UTILIZATION +
        temporal   * WEIGHT_TEMPORAL_FAIRNESS +
        fatigue    * WEIGHT_FATIGUE_CAPACITY
    )

    # If fatigued, composite drops to 0 (safety floor)
    if is_fatigued:
        composite = 0.0

    return {
        "income_parity": income,
        "geographic_burden": geographic,
        "skill_utilization": skill,
        "temporal_fairness": temporal,
        "fatigue_capacity": fatigue,
        "composite_equity_score": round(min(100.0, max(0.0, composite)), 1),
        "is_fatigued": is_fatigued,
        "dimension_contributions": {
            "income_parity": round(income * WEIGHT_INCOME_PARITY, 1),
            "geographic_burden": round(geographic * WEIGHT_GEOGRAPHIC_BURDEN, 1),
            "skill_utilization": round(skill * WEIGHT_SKILL_UTILIZATION, 1),
            "temporal_fairness": round(temporal * WEIGHT_TEMPORAL_FAIRNESS, 1),
            "fatigue_capacity": round(fatigue * WEIGHT_FATIGUE_CAPACITY, 1),
        },
    }


def get_cooperative_equity_dashboard(db: Session, workers: List[Worker]) -> Dict:
    """
    Generate cooperative-wide equity analytics for the admin dashboard.

    Returns aggregate equity statistics across all workers plus per-worker breakdowns.
    """
    worker_equities = []
    dimension_totals = {
        "income_parity": 0.0,
        "geographic_burden": 0.0,
        "skill_utilization": 0.0,
        "temporal_fairness": 0.0,
        "fatigue_capacity": 0.0,
    }

    for worker in workers:
        equity = calculate_equity_score(db, worker)
        # Get worker name
        user = worker.user
        worker_name = user.name if user else f"Worker #{worker.id}"

        worker_equities.append({
            "worker_id": worker.id,
            "worker_name": worker_name,
            "profession": worker.profession,
            "total_jobs": worker.total_jobs,
            "equity": equity,
        })

        for dim in dimension_totals:
            dimension_totals[dim] += equity.get(dim, 0)

    count = max(len(workers), 1)
    dimension_averages = {k: round(v / count, 1) for k, v in dimension_totals.items()}

    # Compute Gini-like inequality index (standard deviation of composite scores)
    composites = [w["equity"]["composite_equity_score"] for w in worker_equities]
    if composites:
        mean_composite = sum(composites) / len(composites)
        variance = sum((c - mean_composite) ** 2 for c in composites) / len(composites)
        inequality_index = round(variance ** 0.5, 1)  # Standard deviation
    else:
        mean_composite = 0
        inequality_index = 0

    return {
        "total_workers": len(workers),
        "mean_equity_score": round(mean_composite, 1),
        "inequality_index": inequality_index,
        "dimension_averages": dimension_averages,
        "fatigued_workers": sum(1 for w in worker_equities if w["equity"]["is_fatigued"]),
        "worker_equities": worker_equities,
    }
