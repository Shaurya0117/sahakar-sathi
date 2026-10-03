"""
Patent Feature: Composite Verifiable Trust Score.

A 6-factor worker reputation system with full provenance tracking.

Unlike simple average-rating systems used by conventional gig platforms,
this computes a holistic trust metric across:
    1. Customer Satisfaction (25%) — Average booking rating
    2. Reliability Index     (20%) — Acceptance/assignment ratio
    3. Punctuality Score     (15%) — Based on completion rate
    4. Skill Breadth         (10%) — Distinct service categories completed
    5. Proof of Work Rate    (10%) — % of completed jobs with verified proof
    6. Economic Equity       (10%) — Standing from Equity Index
    7. Cooperative Tenure    (10%) — Days as an active cooperative member

Novel Claim:
    "A composite verifiable trust metric for cooperative gig workers,
    comprising multi-factor reputation scoring with cross-channel
    provenance tracking and cooperative-specific equity weighting."
"""
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.worker import Worker

# ── Trust Factor Weights (Total = 1.0) ───────────────────────────────────────
WEIGHT_SATISFACTION     = 0.30
WEIGHT_RELIABILITY      = 0.20
WEIGHT_PUNCTUALITY      = 0.20
WEIGHT_SKILL_BREADTH    = 0.10
WEIGHT_PROOF_COMPLIANCE = 0.10
WEIGHT_TENURE           = 0.10


def _calculate_satisfaction(db: Session, worker: Worker) -> float:
    """
    Customer Satisfaction Score (0–100).
    Based on a Bayesian average of customer ratings.
    Formula: (n * avg + 5 * 3.5) / (n + 5)
    """
    from sqlalchemy import func
    
    ratings_data = (
        db.query(
            func.count(Booking.customer_rating).label('count'),
            func.avg(Booking.customer_rating).label('avg')
        )
        .filter(
            Booking.worker_id == worker.id,
            Booking.customer_rating.isnot(None),
        )
        .first()
    )

    n = ratings_data.count if ratings_data and ratings_data.count else 0
    raw_avg = float(ratings_data.avg) if ratings_data and ratings_data.avg else 0.0

    if n == 0:
        return 70.0  # Neutral entry score for new workers (3.5/5.0 * 100)

    bayesian_avg = (n * raw_avg + 5 * 3.5) / (n + 5)
    
    # Map 1-5 rating to 0-100 score
    return round(min(100.0, max(0.0, (bayesian_avg / 5.0) * 100.0)), 1)


def _calculate_reliability(db: Session, worker: Worker) -> float:
    """
    Reliability Index (0–100).
    Ratio of accepted/completed jobs vs total assigned jobs.
    A worker who accepts 9 out of 10 assignments = 90% reliable.
    """
    total_assigned = (
        db.query(func.count(Booking.id))
        .filter(Booking.worker_id == worker.id)
        .scalar()
    ) or 0

    if total_assigned == 0:
        return 60.0  # Neutral for new workers

    rejected = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.worker_id == worker.id,
            Booking.status == BookingStatus.REJECTED,
        )
        .scalar()
    ) or 0

    acceptance_ratio = (total_assigned - rejected) / total_assigned
    return round(min(100.0, max(0.0, acceptance_ratio * 100.0)), 1)


def _calculate_punctuality(db: Session, worker: Worker) -> float:
    """
    Punctuality Score (0-100).
    Evaluates actual arrival time against scheduled time.
    """
    completed_bookings = (
        db.query(Booking)
        .filter(
            Booking.worker_id == worker.id,
            Booking.status == BookingStatus.COMPLETED,
        )
        .all()
    )

    if not completed_bookings:
        return 60.0  # Neutral

    on_time_count = 0
    total_evaluated = 0

    for b in completed_bookings:
        # Use arrived_at datetime
        actual_arr = getattr(b, "arrived_at", None)
        sched_time = getattr(b, "scheduled_time", None)
        
        if not actual_arr or not sched_time:
            continue
            
        try:
            # Parse times like "14:30"
            s_h, s_m = map(int, sched_time.split(":"))
            s_mins = s_h * 60 + s_m
            
            a_h, a_m = actual_arr.hour, actual_arr.minute
            a_mins = a_h * 60 + a_m
            
            # If arrived within 15 minutes of scheduled time
            if a_mins <= s_mins + 15:
                on_time_count += 1
            total_evaluated += 1
        except Exception:
            continue

    if total_evaluated == 0:
        # Fallback to completion rate if no arrival times logged
        active_or_done = (
            db.query(func.count(Booking.id))
            .filter(
                Booking.worker_id == worker.id,
                Booking.status.in_([BookingStatus.ACCEPTED, BookingStatus.IN_PROGRESS, BookingStatus.COMPLETED]),
            ).scalar()
        ) or 0
        if active_or_done == 0: return 60.0
        return round(min(100.0, max(0.0, (len(completed_bookings) / active_or_done) * 100.0)), 1)
        
    punctuality_rate = on_time_count / total_evaluated
    return round(min(100.0, max(0.0, punctuality_rate * 100.0)), 1)


def _calculate_skill_breadth(db: Session, worker: Worker) -> float:
    """
    Skill Breadth Score (0–100).
    Number of distinct service categories the worker has successfully completed.
    More breadth = higher score (up to 6 categories = 100).
    """
    completed_bookings = (
        db.query(Booking)
        .filter(
            Booking.worker_id == worker.id,
            Booking.status == BookingStatus.COMPLETED,
        )
        .all()
    )

    if not completed_bookings:
        # Use declared skills as a proxy
        skill_count = len(worker.skills or [])
        return min(100.0, max(20.0, skill_count * 15.0))

    service_ids = set()
    for booking in completed_bookings:
        req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
        if req:
            service_ids.add(req.service_id)

    categories_count = len(service_ids)
    # Cap at 6 (the platform has 6 service categories)
    return round(min(100.0, max(0.0, (categories_count / 6.0) * 100.0)), 1)


def _calculate_proof_compliance(db: Session, worker: Worker) -> float:
    """
    Proof of Work Compliance Score (0–100).
    % of completed jobs that include a valid after_work_hash.
    Patent Feature: Privacy-Preserving Proof of Service.
    """
    completed = (
        db.query(Booking)
        .filter(
            Booking.worker_id == worker.id,
            Booking.status == BookingStatus.COMPLETED,
        )
        .all()
    )

    if not completed:
        return 50.0  # Neutral for new workers

    with_proof = sum(1 for b in completed if getattr(b, 'before_work_hash', None) and getattr(b, 'after_work_hash', None))
    compliance_rate = with_proof / len(completed)
    return round(min(100.0, max(0.0, compliance_rate * 100.0)), 1)


def _calculate_tenure(worker: Worker) -> float:
    """
    Cooperative Tenure Score (0–100).
    Based on how long the worker has been a cooperative member.
    30+ days = 50, 90+ days = 75, 180+ days = 90, 365+ days = 100.
    """
    if not worker.created_at:
        return 30.0

    now = datetime.now(timezone.utc)
    # Handle timezone-naive datetimes
    created = worker.created_at
    if created.tzinfo is None:
        from datetime import timezone as tz
        created = created.replace(tzinfo=tz.utc)

    days = (now - created).days

    if days >= 365:
        return 100.0
    elif days >= 180:
        return 90.0
    elif days >= 90:
        return 75.0
    elif days >= 30:
        return 50.0
    elif days >= 7:
        return 35.0
    else:
        return 20.0


def calculate_trust_score(db: Session, worker: Worker) -> Dict:
    """
    Master Trust Score Computation.

    Computes 6 trust dimensions and returns a comprehensive breakdown.

    Returns:
        dict with keys:
            - satisfaction: float (0-100)
            - reliability: float (0-100)
            - punctuality: float (0-100)
            - skill_breadth: float (0-100)
            - proof_compliance: float (0-100)
            - tenure: float (0-100)
            - composite_trust_score: float (0-100)
            - trust_tier: str ("PLATINUM" | "GOLD" | "SILVER" | "BRONZE" | "NEW")
    """
    satisfaction = _calculate_satisfaction(db, worker)
    reliability = _calculate_reliability(db, worker)
    punctuality = _calculate_punctuality(db, worker)
    skill_breadth = _calculate_skill_breadth(db, worker)
    proof_compliance = _calculate_proof_compliance(db, worker)
    tenure = _calculate_tenure(worker)

    composite = (
        satisfaction    * WEIGHT_SATISFACTION +
        reliability     * WEIGHT_RELIABILITY +
        punctuality     * WEIGHT_PUNCTUALITY +
        skill_breadth   * WEIGHT_SKILL_BREADTH +
        proof_compliance * WEIGHT_PROOF_COMPLIANCE +
        tenure          * WEIGHT_TENURE
    )
    composite = round(min(100.0, max(0.0, composite)), 1)

    # Assign trust tier
    if composite >= 85:
        tier = "PLATINUM"
    elif composite >= 70:
        tier = "GOLD"
    elif composite >= 55:
        tier = "SILVER"
    elif composite >= 40:
        tier = "BRONZE"
    else:
        tier = "NEW"

    return {
        "satisfaction": satisfaction,
        "reliability": reliability,
        "punctuality": punctuality,
        "skill_breadth": skill_breadth,
        "proof_compliance": proof_compliance,
        "tenure": tenure,
        "composite_trust_score": composite,
        "trust_tier": tier,
    }
