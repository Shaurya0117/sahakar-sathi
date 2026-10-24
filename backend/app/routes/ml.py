"""
Machine Learning Status Routes.

Provides transparency and diagnostics for the ML module (Admin only).
"""
import json
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.config import settings
from app.database.session import get_db
from app.models.user import User
from app.ml.predictor import is_acceptance_model_ready, is_duration_model_ready

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
        "metrics": metrics_data,
    }
