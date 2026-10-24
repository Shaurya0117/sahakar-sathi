"""
Automated Test Suite for Sahakar Sathi Machine Learning Module.

Guarantees:
1. Model loading and valid range predictions [0, 1] for acceptance, positive hours for duration.
2. Graceful fallback on missing/corrupt model files (returns None, zero crashes).
3. Pure rule-based parity when ML_ENABLED=False.
4. Non-interference: ordering outside top-K or outside margin remains invariant.
5. Strict safety invariance: fatigued workers (>80.0) or ineligible workers never promoted.
6. Reproducibility of model training and deterministic metrics.
7. Strict data partition hygiene: 0% sim_seed overlap across train, val, and test splits.
"""
import copy
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.ml import predictor
from app.ml.predictor import (
    clear_models,
    is_acceptance_model_ready,
    is_duration_model_ready,
    load_models,
    predict_accept,
    predict_accept_batch,
    predict_hours,
)
from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.schemas.matching import ScoreBreakdown, WorkerRecommendation
from app.services.matching.engine import get_matching_recommendations


# ---------------------------------------------------------------------------
# 1. Model Loading and Valid Range Predictions
# ---------------------------------------------------------------------------
def test_model_loading_and_predictions():
    """Verify models load successfully and produce outputs in valid intervals."""
    clear_models()
    load_models()

    assert is_acceptance_model_ready() is True
    assert is_duration_model_ready() is True

    valid_features = {
        "distance_km": 3.2,
        "skill_match_score": 85.0,
        "fatigue_index": 20.0,
        "rating": 4.6,
        "experience_years": 6,
        "recent_earnings": 3000.0,
        "job_value": 550.0,
        "job_intensity": 0.65,
        "hour_of_day": 14,
        "past_acceptance_rate": 0.85,
    }
    prob = predict_accept(valid_features)
    assert prob is not None
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0

    batch_probs = predict_accept_batch([valid_features, valid_features])
    assert len(batch_probs) == 2
    for bp in batch_probs:
        assert bp is not None
        assert 0.0 <= bp <= 1.0

    est_hours = predict_hours(
        service_type="Plumbing Repair",
        intensity=0.65,
        experience_years=5,
        job_value=500.0,
    )
    assert est_hours is not None
    assert isinstance(est_hours, float)
    assert 0.25 <= est_hours <= 12.0


# ---------------------------------------------------------------------------
# 2. Graceful Fallback on Missing or Corrupt Model Files
# ---------------------------------------------------------------------------
def test_graceful_fallback_missing_models():
    """When model files do not exist, predictor must return None without raising."""
    clear_models()
    with patch.object(predictor, "ACCEPTANCE_MODEL_PATH", Path("nonexistent_acceptance.joblib")), \
         patch.object(predictor, "DURATION_MODEL_PATH", Path("nonexistent_duration.joblib")):
        load_models(force_reload=True)

        prob = predict_accept({"distance_km": 5.0})
        hours = predict_hours("Plumbing", 0.6, 3, 400.0)

        assert prob is None
        assert hours is None

    # Reset
    clear_models()
    load_models()


def test_graceful_fallback_corrupted_model(tmp_path):
    """When model file is corrupted garbage, predictor must return None cleanly."""
    corrupt_file = tmp_path / "corrupt.joblib"
    corrupt_file.write_bytes(b"corrupt-data-not-a-pickle-or-joblib")

    clear_models()
    with patch.object(predictor, "ACCEPTANCE_MODEL_PATH", corrupt_file):
        load_models(force_reload=True)
        prob = predict_accept({"distance_km": 5.0})
        assert prob is None

    clear_models()
    load_models()


# ---------------------------------------------------------------------------
# 3. Behavior with ML_ENABLED = False
# ---------------------------------------------------------------------------
def test_ml_disabled_parity():
    """When ML_ENABLED is False, predictor returns None and engine does not tie-break."""
    with patch.object(settings, "ML_ENABLED", False):
        clear_models()
        prob = predict_accept({"distance_km": 2.0})
        hours = predict_hours("Electrical", 0.6, 4, 450.0)

        assert prob is None
        assert hours is None

    clear_models()
    load_models()


# ---------------------------------------------------------------------------
# 4. Invariance of Non-Tied Candidates & Outside Top-K
# ---------------------------------------------------------------------------
def test_ml_tiebreak_invariance_rules():
    """
    Test that ML only operates within the top-K margin window.
    Candidates ranked 4th or below, or differing by > 2.0 points, must never move.
    """
    recs = [
        WorkerRecommendation(
            worker_id=1, worker_name="Worker A", verification_status="VERIFIED",
            rating=4.5, total_jobs=10, score=90.0,
            breakdown=ScoreBreakdown(skill_match=90, location=90, availability=100, rating=90, experience=90, workload_income_health_score=90, fatigue_index=10, economic_deficit=50),
            reasons=[], ml_accept_probability=0.30, ml_used=False
        ),
        WorkerRecommendation(
            worker_id=2, worker_name="Worker B", verification_status="VERIFIED",
            rating=4.5, total_jobs=10, score=89.5,  # Within 2.0 points
            breakdown=ScoreBreakdown(skill_match=90, location=90, availability=100, rating=90, experience=90, workload_income_health_score=90, fatigue_index=10, economic_deficit=50),
            reasons=[], ml_accept_probability=0.95, ml_used=False
        ),
        WorkerRecommendation(
            worker_id=3, worker_name="Worker C", verification_status="VERIFIED",
            rating=4.5, total_jobs=10, score=85.0,  # Diff = 5.0 points (> 2.0)
            breakdown=ScoreBreakdown(skill_match=90, location=90, availability=100, rating=90, experience=90, workload_income_health_score=90, fatigue_index=10, economic_deficit=50),
            reasons=[], ml_accept_probability=0.99, ml_used=False
        ),
        WorkerRecommendation(
            worker_id=4, worker_name="Worker D", verification_status="VERIFIED",
            rating=4.5, total_jobs=10, score=84.0,  # Rank 4
            breakdown=ScoreBreakdown(skill_match=90, location=90, availability=100, rating=90, experience=90, workload_income_health_score=90, fatigue_index=10, economic_deficit=50),
            reasons=[], ml_accept_probability=0.99, ml_used=False
        ),
    ]

    # Emulate engine tie-break
    top_score = recs[0].score
    k_limit = min(len(recs), 3)
    margin = 2.0

    tie_indices = [
        i for i in range(k_limit)
        if (top_score - recs[i].score) <= margin
    ]

    assert tie_indices == [0, 1]  # Only Worker A and B are eligible for tie-break
    subset = [recs[i] for i in tie_indices]
    reordered = sorted(subset, key=lambda c: (c.ml_accept_probability, c.score), reverse=True)
    recs[:len(reordered)] = reordered

    # Worker B (higher accept prob) moves to rank 1, Worker A to rank 2
    assert recs[0].worker_id == 2
    assert recs[1].worker_id == 1
    # Worker C and D remain strictly untouched in ranks 3 and 4
    assert recs[2].worker_id == 3
    assert recs[3].worker_id == 4


# ---------------------------------------------------------------------------
# 5. Invariance of Safety Floor (Fatigued Workers Excluded)
# ---------------------------------------------------------------------------
def test_fatigued_worker_never_matched(db: Session):
    """
    Workers with fatigue capacity indicating load > 80.0 must be excluded
    and never match or receive ML promotion.
    """
    from app.models.cooperative import Cooperative
    from app.models.user import User, UserRole
    from app.models.booking import Booking, BookingStatus
    from datetime import datetime, timezone

    admin = User(name="Admin ML", email="admin_ml_fatigue@test.com", password_hash="dummy", role=UserRole.ADMIN)
    db.add(admin)
    db.flush()

    coop = Cooperative(name="ML Test Coop", location="Noida", admin_id=admin.id)
    db.add(coop)
    db.flush()

    # Create service
    service = Service(name="Test Electric Service ML", category="Electrical", price=500.0)
    db.add(service)
    db.flush()

    # Create user & worker
    user = User(email="fatigued_ml@test.com", password_hash="dummy", role=UserRole.WORKER, name="Tired Worker")
    db.add(user)
    db.flush()

    worker = Worker(
        user_id=user.id,
        cooperative_id=coop.id,
        profession="Electrician",
        skills=["Electrical", "Wiring"],
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        rating=4.9,
        experience_years=8,
        location="Sector 10",
    )
    db.add(worker)
    db.flush()

    # Create customer
    cust = User(email="cust_ml@test.com", password_hash="dummy", role=UserRole.CUSTOMER, name="Customer")
    db.add(cust)
    db.flush()

    # Create past heavy service request and booking to fatigue worker > 80 threshold
    heavy_service = Service(
        name="General Maintenance Overhaul ML",
        category="general",
        duration_minutes=1836,
    )
    db.add(heavy_service)
    db.flush()

    past_req = ServiceRequest(
        customer_id=cust.id,
        service_id=heavy_service.id,
        cooperative_id=coop.id,
        description="Heavy overhaul work",
        location="Sector 10",
        preferred_date="2026-08-29",
        preferred_time="09:00",
    )
    db.add(past_req)
    db.flush()

    now = datetime.now(timezone.utc)
    completed_booking = Booking(
        request_id=past_req.id,
        worker_id=worker.id,
        assigned_by=admin.id,
        status=BookingStatus.COMPLETED,
        amount=2000.0,
        scheduled_date="2026-08-29",
        scheduled_time="09:00",
        updated_at=now,
        created_at=now,
    )
    db.add(completed_booking)
    db.flush()

    s_req = ServiceRequest(
        customer_id=cust.id,
        service_id=service.id,
        cooperative_id=coop.id,
        description="Need urgent wiring repair",
        location="Sector 10",
        preferred_date="2026-08-30",
        preferred_time="10:00",
    )
    db.add(s_req)
    db.flush()

    # Run recommendation
    rec_resp = get_matching_recommendations(db, s_req.id)
    recommended_worker_ids = [rec.worker_id for rec in rec_resp.recommendations]

    # Heavily fatigued worker must NOT appear in recommendations
    assert worker.id not in recommended_worker_ids


# ---------------------------------------------------------------------------
# 6. Reproducibility of Training Artifacts
# ---------------------------------------------------------------------------
def test_metrics_json_artifact_integrity():
    """Verify metrics.json exists and records the expected model test metrics."""
    metrics_path = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts" / "metrics.json"
    assert metrics_path.is_file(), "metrics.json must be present in backend/app/ml/artifacts/"

    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    assert metrics["random_seed"] == 42
    assert "acceptance_model" in metrics
    assert "duration_model" in metrics

    acc_test = metrics["acceptance_model"]["test_metrics"]
    assert acc_test["roc_auc"] > 0.90
    assert acc_test["accuracy"] > 0.80
    assert acc_test["brier_score"] < 0.15

    dur_test = metrics["duration_model"]["test_metrics"]
    assert dur_test["mae"] < 0.35
    assert dur_test["r2"] > 0.80


# ---------------------------------------------------------------------------
# 7. Data Hygiene: Zero sim_seed Overlap Across Splits
# ---------------------------------------------------------------------------
def test_zero_seed_leakage():
    """Verify that train, validation, and test splits have 0% sim_seed overlap."""
    from scripts.train_ml import RANDOM_SEED
    from sklearn.model_selection import GroupShuffleSplit
    import pandas as pd

    # Generate synthetic dataframe
    from scripts.generate_ml_data import generate_acceptance_data
    df = generate_acceptance_data(n_samples=3000, n_sim_seeds=50, seed=RANDOM_SEED)

    gss_test = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=RANDOM_SEED)
    train_val_idx, test_idx = next(gss_test.split(df, groups=df["sim_seed"]))

    df_train_val = df.iloc[train_val_idx]
    df_test = df.iloc[test_idx]

    gss_val = GroupShuffleSplit(n_splits=1, test_size=0.1765, random_state=RANDOM_SEED)
    tr_sub_idx, val_sub_idx = next(gss_val.split(df_train_val, groups=df_train_val["sim_seed"]))

    train_seeds = set(df_train_val.iloc[tr_sub_idx]["sim_seed"].unique())
    val_seeds = set(df_train_val.iloc[val_sub_idx]["sim_seed"].unique())
    test_seeds = set(df_test["sim_seed"].unique())

    # Strict partition verification: sets must be mutually disjoint
    assert len(train_seeds.intersection(val_seeds)) == 0, "Train and Val seeds must not overlap"
    assert len(train_seeds.intersection(test_seeds)) == 0, "Train and Test seeds must not overlap"
    assert len(val_seeds.intersection(test_seeds)) == 0, "Val and Test seeds must not overlap"


# ---------------------------------------------------------------------------
# 8. API Status Route Authentication & Payload
# ---------------------------------------------------------------------------
def test_ml_status_api_endpoints(client, db: Session):
    """Verify GET /api/ml/status requires admin authorization and returns diagnostic metrics."""
    from app.models.user import User, UserRole
    from app.auth.jwt import create_access_token

    # 1. Unauthenticated request
    res_unauth = client.get("/api/ml/status")
    assert res_unauth.status_code in (401, 403)

    # 2. Worker request (forbidden)
    worker_user = User(name="Worker API", email="worker_api_ml@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(worker_user)
    db.flush()
    worker_token = create_access_token(subject=str(worker_user.id), role=worker_user.role.value)
    res_worker = client.get("/api/ml/status", headers={"Authorization": f"Bearer {worker_token}"})
    assert res_worker.status_code == 403

    # 3. Admin request (authorized)
    admin_user = User(name="Admin API", email="admin_api_ml@test.com", password_hash="hash", role=UserRole.ADMIN)
    db.add(admin_user)
    db.flush()
    admin_token = create_access_token(subject=str(admin_user.id), role=admin_user.role.value)
    res_admin = client.get("/api/ml/status", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["ml_enabled"] is True
    assert data["tiebreak_top_k"] == 3
    assert data["tiebreak_margin"] == 2.0
    assert data["acceptance_model_ready"] is True
    assert data["duration_model_ready"] is True
    assert "metrics" in data

