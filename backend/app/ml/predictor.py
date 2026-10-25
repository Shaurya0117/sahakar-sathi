"""
Machine Learning Predictor Module for Sahakar Sathi.

Provides runtime inference wrappers for:
1. Worker offer acceptance probability (Calibrated HistGradientBoostingClassifier)
2. Service duration estimation (HistGradientBoostingRegressor)

Ensures robust fallback: if ML_ENABLED is False or models are unavailable/corrupted,
silently returns None so callers fall back to deterministic rule-based algorithms.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import joblib

from app.config import settings

logger = logging.getLogger(__name__)

# Artifact locations
ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ACCEPTANCE_MODEL_PATH = ARTIFACTS_DIR / "acceptance.joblib"
DURATION_MODEL_PATH = ARTIFACTS_DIR / "duration.joblib"
CHURN_MODEL_PATH = ARTIFACTS_DIR / "churn.joblib"
REVIEW_FRAUD_MODEL_PATH = ARTIFACTS_DIR / "review_fraud.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

_acceptance_model = None
_duration_model = None
_churn_model = None
_review_fraud_model = None
_load_attempted = False


def load_models(force_reload: bool = False) -> None:
    """Lazy load models with fault tolerance."""
    global _acceptance_model, _duration_model, _churn_model, _review_fraud_model, _load_attempted
    if _load_attempted and not force_reload:
        return

    _load_attempted = True

    if not getattr(settings, "ML_ENABLED", True):
        logger.debug("ML is disabled in configuration. Skipping model loading.")
        _acceptance_model = None
        _duration_model = None
        _churn_model = None
        _review_fraud_model = None
        return

    try:
        if ACCEPTANCE_MODEL_PATH.is_file():
            _acceptance_model = joblib.load(ACCEPTANCE_MODEL_PATH)
            logger.info("Loaded acceptance classifier from %s", ACCEPTANCE_MODEL_PATH)
        else:
            logger.warning("Acceptance model file not found at %s", ACCEPTANCE_MODEL_PATH)
            _acceptance_model = None
    except Exception as exc:
        logger.warning("Failed to load acceptance model: %s", exc)
        _acceptance_model = None

    try:
        if DURATION_MODEL_PATH.is_file():
            _duration_model = joblib.load(DURATION_MODEL_PATH)
            logger.info("Loaded duration regressor from %s", DURATION_MODEL_PATH)
        else:
            logger.warning("Duration model file not found at %s", DURATION_MODEL_PATH)
            _duration_model = None
    except Exception as exc:
        logger.warning("Failed to load duration model: %s", exc)
        _duration_model = None

    try:
        if CHURN_MODEL_PATH.is_file():
            _churn_model = joblib.load(CHURN_MODEL_PATH)
            logger.info("Loaded churn classifier from %s", CHURN_MODEL_PATH)
        else:
            logger.warning("Churn model file not found at %s", CHURN_MODEL_PATH)
            _churn_model = None
    except Exception as exc:
        logger.warning("Failed to load churn model: %s", exc)
        _churn_model = None

    try:
        if REVIEW_FRAUD_MODEL_PATH.is_file():
            _review_fraud_model = joblib.load(REVIEW_FRAUD_MODEL_PATH)
            logger.info("Loaded review fraud IsolationForest from %s", REVIEW_FRAUD_MODEL_PATH)
        else:
            logger.warning("Review fraud model file not found at %s", REVIEW_FRAUD_MODEL_PATH)
            _review_fraud_model = None
    except Exception as exc:
        logger.warning("Failed to load review fraud model: %s", exc)
        _review_fraud_model = None


def clear_models() -> None:
    """Clear cached models (useful for testing fallback mechanisms)."""
    global _acceptance_model, _duration_model, _churn_model, _review_fraud_model, _load_attempted
    _acceptance_model = None
    _duration_model = None
    _churn_model = None
    _review_fraud_model = None
    _load_attempted = False


def is_acceptance_model_ready() -> bool:
    load_models()
    return _acceptance_model is not None and getattr(settings, "ML_ENABLED", True)


def is_duration_model_ready() -> bool:
    load_models()
    return _duration_model is not None and getattr(settings, "ML_ENABLED", True)


def is_churn_model_ready() -> bool:
    load_models()
    return _churn_model is not None and getattr(settings, "ML_ENABLED", True)


def is_review_fraud_model_ready() -> bool:
    load_models()
    return _review_fraud_model is not None and getattr(settings, "ML_ENABLED", True)


def predict_accept(features_dict: Dict[str, Any]) -> Optional[float]:
    """
    Predict acceptance probability of a job offer by a worker.

    Expected keys in features_dict:
    - distance_km (0.0 to 50.0)
    - skill_match_score (0.0 to 100.0)
    - fatigue_index (0.0 to 100.0)
    - rating (1.0 to 5.0)
    - experience_years (0 to 50)
    - recent_earnings (0.0 to 100000.0)
    - job_value (100.0 to 10000.0)
    - job_intensity (0.1 to 1.0)
    - hour_of_day (0 to 23)
    - past_acceptance_rate (0.0 to 1.0)

    Returns:
        float probability in [0.0, 1.0], or None on error or when ML is disabled.
    """
    if not is_acceptance_model_ready():
        return None

    try:
        dist = float(np.clip(float(features_dict.get("distance_km", 5.0)), 0.0, 50.0))
        skill = float(np.clip(float(features_dict.get("skill_match_score", 50.0)), 0.0, 100.0))
        fatigue = float(np.clip(float(features_dict.get("fatigue_index", 0.0)), 0.0, 100.0))
        rating = float(np.clip(float(features_dict.get("rating", 4.0)), 1.0, 5.0))
        exp = float(np.clip(float(features_dict.get("experience_years", 0)), 0.0, 50.0))
        earnings = float(np.clip(float(features_dict.get("recent_earnings", 2500.0)), 0.0, 100000.0))
        job_val = float(np.clip(float(features_dict.get("job_value", 500.0)), 100.0, 10000.0))
        intensity = float(np.clip(float(features_dict.get("job_intensity", 0.6)), 0.1, 1.0))
        hour = int(np.clip(int(features_dict.get("hour_of_day", 12)), 0, 23))
        past_rate = float(np.clip(float(features_dict.get("past_acceptance_rate", 0.8)), 0.0, 1.0))

        row_df = pd.DataFrame([{
            "distance_km": dist,
            "skill_match_score": skill,
            "fatigue_index": fatigue,
            "rating": rating,
            "experience_years": exp,
            "recent_earnings": earnings,
            "job_value": job_val,
            "job_intensity": intensity,
            "hour_of_day": hour,
            "past_acceptance_rate": past_rate,
        }])

        prob = float(_acceptance_model.predict_proba(row_df)[0, 1])
        prob = max(0.0, min(1.0, prob))
        return round(prob, 4)
    except Exception as exc:
        logger.warning("predict_accept failed: %s", exc)
        return None


def predict_accept_batch(features_list: list) -> list:
    """
    Predict acceptance probabilities for a batch of candidate offers.
    Returns list of float probabilities (or None for failures/disabled).
    """
    if not is_acceptance_model_ready() or not features_list:
        return [None] * len(features_list)

    try:
        rows = []
        for features_dict in features_list:
            dist = float(np.clip(float(features_dict.get("distance_km", 5.0)), 0.0, 50.0))
            skill = float(np.clip(float(features_dict.get("skill_match_score", 50.0)), 0.0, 100.0))
            fatigue = float(np.clip(float(features_dict.get("fatigue_index", 0.0)), 0.0, 100.0))
            rating = float(np.clip(float(features_dict.get("rating", 4.0)), 1.0, 5.0))
            exp = float(np.clip(float(features_dict.get("experience_years", 0)), 0.0, 50.0))
            earnings = float(np.clip(float(features_dict.get("recent_earnings", 2500.0)), 0.0, 100000.0))
            job_val = float(np.clip(float(features_dict.get("job_value", 500.0)), 100.0, 10000.0))
            intensity = float(np.clip(float(features_dict.get("job_intensity", 0.6)), 0.1, 1.0))
            hour = int(np.clip(int(features_dict.get("hour_of_day", 12)), 0, 23))
            past_rate = float(np.clip(float(features_dict.get("past_acceptance_rate", 0.8)), 0.0, 1.0))
            rows.append({
                "distance_km": dist,
                "skill_match_score": skill,
                "fatigue_index": fatigue,
                "rating": rating,
                "experience_years": exp,
                "recent_earnings": earnings,
                "job_value": job_val,
                "job_intensity": intensity,
                "hour_of_day": hour,
                "past_acceptance_rate": past_rate,
            })
        batch_df = pd.DataFrame(rows)
        probs = _acceptance_model.predict_proba(batch_df)[:, 1]
        return [round(float(max(0.0, min(1.0, p))), 4) for p in probs]
    except Exception as exc:
        logger.warning("predict_accept_batch failed: %s", exc)
        return [None] * len(features_list)


def predict_hours(
    service_type: str,
    intensity: float,
    experience_years: int,
    job_value: float,
) -> Optional[float]:
    """
    Predict job completion duration in hours.

    Returns:
        float hours in [0.25, 12.0], or None on error or when ML is disabled.
    """
    if not is_duration_model_ready():
        return None

    try:
        st = str(service_type or "General")
        inten = float(np.clip(float(intensity or 0.5), 0.1, 1.0))
        exp = float(np.clip(float(experience_years or 0), 0.0, 50.0))
        val = float(np.clip(float(job_value or 500.0), 100.0, 10000.0))

        row_df = pd.DataFrame([{
            "service_type": st,
            "job_intensity": inten,
            "experience_years": exp,
            "job_value": val,
        }])

        predicted_hours = float(_duration_model.predict(row_df)[0])
        predicted_hours = max(0.25, min(12.0, predicted_hours))
        return round(predicted_hours, 2)
    except Exception as exc:
        logger.warning("predict_hours failed: %s", exc)
        return None


def predict_churn(features_dict: Dict[str, Any]) -> Optional[float]:
    """
    Predict probability that a worker will churn (become inactive) in the next 30 days.

    Expected keys in features_dict:
    - days_since_last_booking (0 to 90)
    - bookings_last_30d (0 to 20)
    - earnings_last_30d (0 to 15000)
    - acceptance_rate (0.0 to 1.0)
    - avg_fatigue_index (0.0 to 95.0)
    - rating (1.0 to 5.0)
    - experience_years (0 to 15)
    - days_on_platform (1 to 1000)
    - earnings_trend (-1.0 to 1.0)

    Returns:
        float probability in [0.0, 1.0] (P(churn)), or None on error or when ML is disabled.
    """
    if not is_churn_model_ready():
        return None

    try:
        days_since = float(np.clip(float(features_dict.get("days_since_last_booking", 30.0)), 0.0, 90.0))
        bookings_30d = float(np.clip(float(features_dict.get("bookings_last_30d", 2)), 0.0, 20.0))
        earnings_30d = float(np.clip(float(features_dict.get("earnings_last_30d", 1500.0)), 0.0, 15000.0))
        acc_rate = float(np.clip(float(features_dict.get("acceptance_rate", 0.5)), 0.0, 1.0))
        fatigue = float(np.clip(float(features_dict.get("avg_fatigue_index", 0.0)), 0.0, 95.0))
        rating = float(np.clip(float(features_dict.get("rating", 3.0)), 1.0, 5.0))
        exp_years = float(np.clip(float(features_dict.get("experience_years", 0)), 0.0, 15.0))
        days_on = float(np.clip(float(features_dict.get("days_on_platform", 100)), 1.0, 1000.0))
        trend = float(np.clip(float(features_dict.get("earnings_trend", 0.0)), -1.0, 1.0))

        row_df = pd.DataFrame([{
            "days_since_last_booking": days_since,
            "bookings_last_30d": bookings_30d,
            "earnings_last_30d": earnings_30d,
            "acceptance_rate": acc_rate,
            "avg_fatigue_index": fatigue,
            "rating": rating,
            "experience_years": exp_years,
            "days_on_platform": days_on,
            "earnings_trend": trend,
        }])

        prob = float(_churn_model.predict_proba(row_df)[0, 1])
        prob = max(0.0, min(1.0, prob))
        return round(prob, 4)
    except Exception as exc:
        logger.warning("predict_churn failed: %s", exc)
        return None


def predict_review_anomaly(features_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evaluate review and rating parameters using unsupervised Isolation Forest.

    Expected keys in features_dict:
    - rating_value: float (1.0 to 5.0)
    - review_length: int (0 to 1000)
    - booking_amount: float (100.0 to 10000.0)
    - worker_tenure_days: int (1 to 1000)
    - worker_recent_booking_count: int (0 to 50)
    - rating_deviation_from_worker_mean: float (0.0 to 4.0)

    Returns:
        dict with keys:
            - is_anomaly: bool
            - anomaly_score: float in [0.0, 1.0] (higher = more anomalous)
            - risk_level: "NORMAL" | "SUSPICIOUS" | "ANOMALOUS"
            - raw_decision_score: float
        or None if disabled or model not ready.
    """
    if not is_review_fraud_model_ready():
        return None

    try:
        r_val = float(np.clip(float(features_dict.get("rating_value", 5.0)), 1.0, 5.0))
        r_len = int(np.clip(int(features_dict.get("review_length", 50)), 0, 1000))
        b_amt = float(np.clip(float(features_dict.get("booking_amount", 500.0)), 50.0, 10000.0))
        w_ten = int(np.clip(int(features_dict.get("worker_tenure_days", 100)), 1, 1000))
        w_rec = int(np.clip(int(features_dict.get("worker_recent_booking_count", 4)), 0, 50))
        r_dev = float(np.clip(float(features_dict.get("rating_deviation_from_worker_mean", 0.2)), 0.0, 4.0))

        row_df = pd.DataFrame([{
            "rating_value": r_val,
            "review_length": r_len,
            "booking_amount": b_amt,
            "worker_tenure_days": w_ten,
            "worker_recent_booking_count": w_rec,
            "rating_deviation_from_worker_mean": r_dev,
        }])

        raw_pred = int(_review_fraud_model.predict(row_df)[0])
        raw_score = float(_review_fraud_model.decision_function(row_df)[0])

        # Normalize score: decision_function typically in [-0.25, 0.20]
        # Invert so higher values indicate higher anomaly likelihood
        # Map roughly: raw -0.2 -> 0.85, raw 0.0 -> 0.50, raw +0.2 -> 0.15
        norm_score = float(np.clip(0.50 - (raw_score * 1.8), 0.0, 1.0))

        is_anomaly = (raw_pred == -1) or (norm_score >= 0.65)
        if norm_score >= 0.65:
            risk = "ANOMALOUS"
        elif norm_score >= 0.50:
            risk = "SUSPICIOUS"
        else:
            risk = "NORMAL"

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(norm_score, 4),
            "risk_level": risk,
            "raw_decision_score": round(raw_score, 4),
        }
    except Exception as exc:
        logger.warning("predict_review_anomaly failed: %s", exc)
        return None
