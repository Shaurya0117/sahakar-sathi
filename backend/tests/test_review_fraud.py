"""
Unit tests for Review Fraud and Rating Anomaly Detection (IsolationForest).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ml-tests")

import pytest
from app.ml.predictor import (
    is_review_fraud_model_ready,
    predict_review_anomaly,
    clear_models,
)
from app.config import settings


def test_review_fraud_model_is_ready():
    assert is_review_fraud_model_ready() is True


def test_normal_review_classified_as_normal():
    # A realistic 4-star review with standard text, standard price, normal tenure
    normal_features = {
        "rating_value": 4.5,
        "review_length": 85,
        "booking_amount": 650.0,
        "worker_tenure_days": 180,
        "worker_recent_booking_count": 4,
        "rating_deviation_from_worker_mean": 0.2,
    }
    result = predict_review_anomaly(normal_features)
    assert result is not None
    assert "is_anomaly" in result
    assert "anomaly_score" in result
    assert "risk_level" in result
    assert 0.0 <= result["anomaly_score"] <= 1.0
    assert result["risk_level"] in ("NORMAL", "SUSPICIOUS")


def test_collusion_burst_flagged_as_anomalous():
    # An extreme collusion burst: 5-star rating, 0 text, tenure of 1 day, 30 bookings in 14 days
    anomalous_features = {
        "rating_value": 5.0,
        "review_length": 0,
        "booking_amount": 100.0,
        "worker_tenure_days": 1,
        "worker_recent_booking_count": 30,
        "rating_deviation_from_worker_mean": 0.1,
    }
    result = predict_review_anomaly(anomalous_features)
    assert result is not None
    assert result["is_anomaly"] is True or result["risk_level"] in ("ANOMALOUS", "SUSPICIOUS")
    assert result["anomaly_score"] > 0.50


def test_competitor_sabotage_flagged():
    # 1-star rating on high price, huge deviation from worker's 4.8 baseline
    sabotage_features = {
        "rating_value": 1.0,
        "review_length": 5,
        "booking_amount": 250.0,
        "worker_tenure_days": 350,
        "worker_recent_booking_count": 2,
        "rating_deviation_from_worker_mean": 3.8,
    }
    result = predict_review_anomaly(sabotage_features)
    assert result is not None
    assert result["anomaly_score"] > 0.50


def test_graceful_fallback_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "ML_ENABLED", False)
    clear_models()
    result = predict_review_anomaly({"rating_value": 5.0})
    assert result is None
    monkeypatch.setattr(settings, "ML_ENABLED", True)
    clear_models()
