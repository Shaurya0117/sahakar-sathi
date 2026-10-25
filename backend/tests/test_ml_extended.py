"""Tests for Churn Prediction, Duration Estimator, and Thompson Sampling Bandit."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ml-tests")

import pytest


# ---- Churn model tests ----

def test_churn_predict_returns_float_or_none():
    from app.ml.predictor import predict_churn
    result = predict_churn({
        "days_since_last_booking": 30.0,
        "bookings_last_30d": 2,
        "earnings_last_30d": 1500.0,
        "acceptance_rate": 0.7,
        "avg_fatigue_index": 40.0,
        "rating": 4.2,
        "experience_years": 3,
        "days_on_platform": 200,
        "earnings_trend": 0.1,
    })
    assert result is None or (0.0 <= result <= 1.0)


def test_churn_predict_bounds():
    from app.ml.predictor import predict_churn
    result = predict_churn({
        "days_since_last_booking": 90.0,
        "bookings_last_30d": 0,
        "earnings_last_30d": 0.0,
        "acceptance_rate": 0.1,
        "avg_fatigue_index": 90.0,
        "rating": 1.5,
        "experience_years": 0,
        "days_on_platform": 5,
        "earnings_trend": -1.0,
    })
    if result is not None:
        assert 0.0 <= result <= 1.0


def test_churn_graceful_fallback_when_disabled(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ML_ENABLED", False)
    from app.ml import predictor as pred_module
    pred_module.clear_models()
    result = pred_module.predict_churn({"days_since_last_booking": 10})
    assert result is None
    monkeypatch.setattr(settings, "ML_ENABLED", True)
    pred_module.clear_models()


# ---- Duration model tests ----

def test_duration_predict_returns_float_or_none():
    from app.ml.predictor import predict_hours
    result = predict_hours("Electrician", 0.7, 5, 500.0)
    assert result is None or (0.25 <= result <= 12.0)


def test_duration_predict_clamps_output():
    from app.ml.predictor import predict_hours
    result = predict_hours("Cleaning", 0.5, 0, 300.0)
    if result is not None:
        assert 0.25 <= result <= 12.0


# ---- Bandit tests ----

def test_bandit_sample_best_arm_returns_valid_arm():
    from app.ml.bandit import sample_best_arm, reset_state
    reset_state()
    arm = sample_best_arm("Electrician", 10, rng_seed=42)
    assert arm in (0, 1, 2)


def test_bandit_record_outcome_updates_state():
    from app.ml.bandit import record_outcome, _bandit_state, reset_state, _load_state, _context_key
    reset_state()
    _load_state()
    record_outcome("Plumber", 14, 0, True)
    key = _context_key("Plumber", 14)
    assert _bandit_state[key]["alpha"][0] > 1.0


def test_bandit_record_decline_updates_beta():
    from app.ml.bandit import record_outcome, _bandit_state, reset_state, _load_state, _context_key
    reset_state()
    _load_state()
    record_outcome("Carpenter", 8, 1, False)
    key = _context_key("Carpenter", 8)
    assert _bandit_state[key]["beta"][1] > 1.0


def test_bandit_disabled_returns_zero(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ML_ENABLED", False)
    from app.ml.bandit import sample_best_arm, reset_state
    reset_state()
    arm = sample_best_arm("Electrician", 10)
    assert arm == 0
    monkeypatch.setattr(settings, "ML_ENABLED", True)


def test_bandit_get_stats():
    from app.ml.bandit import get_bandit_stats, reset_state
    reset_state()
    stats = get_bandit_stats()
    assert "total_contexts" in stats
    assert "total_trials" in stats
    assert stats["n_arms"] == 3
