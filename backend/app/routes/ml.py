"""
Machine Learning Status Routes.

Provides transparency and diagnostics for the ML module (Admin only).
Also exposes churn prediction, duration estimation, and bandit endpoints.
"""
import json
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.config import settings
from app.database.session import get_db
from app.models.user import User
from app.models.booking import Booking, BookingStatus
from app.models.worker import Worker
from app.ml.predictor import (
    is_acceptance_model_ready,
    is_duration_model_ready,
    is_churn_model_ready,
    is_review_fraud_model_ready,
    predict_churn,
    predict_hours,
    predict_review_anomaly,
)

ml_router = APIRouter(prefix="/ml", tags=["Machine Learning"])

METRICS_FILE = Path(__file__).resolve().parent.parent / "ml" / "artifacts" / "metrics.json"


@ml_router.get(
    "/status",
    summary="Get machine learning model diagnostics and evaluation metrics (ADMIN only)",
)
def get_ml_status(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns runtime configuration, model availability, and held-out test metrics.
    """
    from app.ml.bandit import get_bandit_stats

    metrics_data = {}
    if METRICS_FILE.is_file():
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = {"error": "Failed to read metrics.json"}

    return {
        "ml_enabled": getattr(settings, "ML_ENABLED", True),
        "tiebreak_top_k": getattr(settings, "ML_TIEBREAK_TOP_K", 3),
        "tiebreak_margin": getattr(settings, "ML_TIEBREAK_MARGIN", 2.0),
        "acceptance_model_ready": is_acceptance_model_ready(),
        "duration_model_ready": is_duration_model_ready(),
        "churn_model_ready": is_churn_model_ready(),
        "review_fraud_model_ready": is_review_fraud_model_ready(),
        "bandit": get_bandit_stats(),
        "metrics": metrics_data,
    }


@ml_router.get(
    "/churn/{worker_id}",
    summary="Predict worker churn probability (ADMIN only)",
)
def get_worker_churn(
    worker_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Predict the probability that a worker will become inactive in the next 30 days.
    Returns risk level: LOW (<0.3), MEDIUM (0.3-0.6), HIGH (>0.6).
    """
    from app.services.matching.equity_graph import calculate_fatigue_capacity

    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found.")

    now = datetime.datetime.utcnow()
    thirty_days_ago = now - datetime.timedelta(days=30)

    # All bookings for this worker
    all_bookings = db.query(Booking).filter(Booking.worker_id == worker_id).all()
    completed_bookings = [b for b in all_bookings if b.status == BookingStatus.COMPLETED]

    # days_since_last_booking
    if completed_bookings:
        latest = max(
            (b.created_at for b in completed_bookings if b.created_at),
            default=None
        )
        if latest:
            delta = now - latest.replace(tzinfo=None) if latest.tzinfo else now - latest
            days_since_last_booking = float(min(90.0, max(0.0, delta.days)))
        else:
            days_since_last_booking = 90.0
    else:
        days_since_last_booking = 90.0

    # bookings_last_30d (count of all bookings in last 30 days)
    bookings_last_30d = sum(
        1 for b in all_bookings
        if b.created_at and b.created_at.replace(tzinfo=None) >= thirty_days_ago
    )

    # earnings_last_30d (sum of amount for COMPLETED bookings in last 30 days)
    earnings_last_30d = sum(
        float(b.amount or 0)
        for b in completed_bookings
        if b.created_at and b.created_at.replace(tzinfo=None) >= thirty_days_ago
    )

    # acceptance_rate
    acceptance_rate = float(getattr(worker, "acceptance_rate", None) or 0.5)

    # avg_fatigue_index: compute from capacity score (fatigue_index = 100 - capacity)
    try:
        capacity = calculate_fatigue_capacity(db, worker)
        avg_fatigue_index = float(max(0.0, 100.0 - capacity))
    except Exception:
        avg_fatigue_index = 0.0

    # rating
    rating = float(worker.rating or 3.0)

    # experience_years
    experience_years = int(worker.experience_years or 0)

    # days_on_platform
    if worker.created_at:
        created = worker.created_at.replace(tzinfo=None) if worker.created_at.tzinfo else worker.created_at
        days_on_platform = max(1, (now - created).days)
    else:
        days_on_platform = 1

    # earnings_trend: (avg last 5 - avg bookings 6-10) / max(1, avg_all)
    sorted_completed = sorted(
        [b for b in completed_bookings if b.amount is not None],
        key=lambda b: b.created_at or datetime.datetime.min,
        reverse=True,
    )
    if len(sorted_completed) >= 6:
        last5_avg = sum(float(b.amount) for b in sorted_completed[:5]) / 5
        next5 = sorted_completed[5:10]
        next5_avg = sum(float(b.amount) for b in next5) / len(next5) if next5 else last5_avg
        all_avg = sum(float(b.amount) for b in sorted_completed) / len(sorted_completed)
        earnings_trend = (last5_avg - next5_avg) / max(1.0, all_avg)
        earnings_trend = float(max(-1.0, min(1.0, earnings_trend)))
    else:
        earnings_trend = 0.0

    features_used = {
        "days_since_last_booking": days_since_last_booking,
        "bookings_last_30d": bookings_last_30d,
        "earnings_last_30d": earnings_last_30d,
        "acceptance_rate": acceptance_rate,
        "avg_fatigue_index": avg_fatigue_index,
        "rating": rating,
        "experience_years": experience_years,
        "days_on_platform": days_on_platform,
        "earnings_trend": earnings_trend,
    }

    churn_prob = predict_churn(features_used)
    model_ready = is_churn_model_ready()

    if churn_prob is None:
        risk_level = "UNKNOWN"
    elif churn_prob < 0.3:
        risk_level = "LOW"
    elif churn_prob <= 0.6:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"

    return {
        "worker_id": worker_id,
        "churn_probability": churn_prob,
        "risk_level": risk_level,
        "features_used": features_used,
        "model_ready": model_ready,
    }


@ml_router.get(
    "/duration-estimate",
    summary="Estimate job duration via ML (authenticated, any role)",
)
def get_duration_estimate(
    service_type: str = Query(..., description="Service type / profession"),
    intensity: float = Query(0.6, ge=0.1, le=1.0, description="Job intensity (0.1–1.0)"),
    experience_years: int = Query(3, ge=0, le=50, description="Worker experience years"),
    job_value: float = Query(500.0, ge=100.0, le=10000.0, description="Job value in INR"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Return ML-predicted job duration for a given service type and context.
    """
    estimated_hours = predict_hours(service_type, intensity, experience_years, job_value)
    model_ready = is_duration_model_ready()

    if estimated_hours is not None:
        h = estimated_hours
        if h < 1.0:
            m = round(h * 60)
            formatted = f"~{m}m"
        else:
            hours_int = int(h)
            mins_int = int((h % 1) * 60)
            if mins_int > 0:
                formatted = f"~{hours_int}h {mins_int}m"
            else:
                formatted = f"~{hours_int}h"
    else:
        formatted = "N/A"

    return {
        "service_type": service_type,
        "estimated_hours": estimated_hours,
        "estimated_hours_formatted": formatted,
        "model_ready": model_ready,
    }


@ml_router.get(
    "/bandit/reset",
    summary="Reset Thompson Sampling bandit state (ADMIN only, for testing)",
)
def reset_bandit(
    admin_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    """Reset bandit learning state and persist the cleared state to disk."""
    from app.ml.bandit import reset_state, _save_state
    reset_state()
    _save_state()
    return {"status": "ok", "message": "Bandit state has been reset."}


@ml_router.get(
    "/review-audit/{booking_id}",
    summary="Audit a booking review for anomalies / fraud using Isolation Forest (ADMIN only)",
)
def audit_booking_review(
    booking_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Examines customer rating and review patterns against the worker's historical
    baseline to detect collusion, sudden rating bursts, or competitor review bombing.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.customer_rating is None:
        return {
            "booking_id": booking_id,
            "reviewed": False,
            "message": "Booking has not been reviewed yet.",
        }

    worker = db.query(Worker).filter(Worker.id == booking.worker_id).first()
    now = datetime.datetime.utcnow()

    # Tenure
    if worker and worker.created_at:
        w_created = worker.created_at.replace(tzinfo=None) if worker.created_at.tzinfo else worker.created_at
        tenure = max(1, (now - w_created).days)
    else:
        tenure = 100

    # Recent bookings count (last 14 days)
    fourteen_days_ago = now - datetime.timedelta(days=14)
    recent_cnt = db.query(Booking).filter(
        Booking.worker_id == booking.worker_id,
        Booking.created_at >= fourteen_days_ago
    ).count()

    # Worker baseline rating
    worker_mean_rating = float(worker.rating or 4.0) if worker else 4.0
    rating_dev = float(abs(booking.customer_rating - worker_mean_rating))

    features = {
        "rating_value": float(booking.customer_rating),
        "review_length": len(booking.customer_review or ""),
        "booking_amount": float(booking.amount or 500.0),
        "worker_tenure_days": tenure,
        "worker_recent_booking_count": recent_cnt,
        "rating_deviation_from_worker_mean": rating_dev,
    }

    audit_result = predict_review_anomaly(features)
    return {
        "booking_id": booking_id,
        "worker_id": booking.worker_id,
        "rating": booking.customer_rating,
        "review_text": booking.customer_review,
        "features_used": features,
        "audit": audit_result,
        "model_ready": is_review_fraud_model_ready(),
    }


@ml_router.post(
    "/review-audit",
    summary="Arbitrary feature review audit testing (ADMIN only)",
)
def audit_arbitrary_review(
    payload: Dict[str, Any],
    admin_user: User = Depends(require_admin),
) -> Dict[str, Any]:
    """Test Isolation Forest review fraud inference on custom feature dictionaries."""
    res = predict_review_anomaly(payload)
    return {
        "payload": payload,
        "audit": res,
        "model_ready": is_review_fraud_model_ready(),
    }
