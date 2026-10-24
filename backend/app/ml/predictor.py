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
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

_acceptance_model = None
_duration_model = None
_load_attempted = False


def load_models(force_reload: bool = False) -> None:
    """Lazy load models with fault tolerance."""
    global _acceptance_model, _duration_model, _load_attempted
    if _load_attempted and not force_reload:
        return

    _load_attempted = True

    if not getattr(settings, "ML_ENABLED", True):
        logger.debug("ML is disabled in configuration. Skipping model loading.")
        _acceptance_model = None
        _duration_model = None
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


def clear_models() -> None:
    """Clear cached models (useful for testing fallback mechanisms)."""
    global _acceptance_model, _duration_model, _load_attempted
    _acceptance_model = None
    _duration_model = None
    _load_attempted = False


def is_acceptance_model_ready() -> bool:
    load_models()
    return _acceptance_model is not None and getattr(settings, "ML_ENABLED", True)


def is_duration_model_ready() -> bool:
    load_models()
    return _duration_model is not None and getattr(settings, "ML_ENABLED", True)


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
