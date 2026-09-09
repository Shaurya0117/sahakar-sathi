"""
Cooperative & Admin analytics routes — /api/cooperative

Endpoints:
    GET /api/cooperative/me     — get primary cooperative details (ADMIN only)
    GET /api/cooperative/stats  — get live workforce statistics (ADMIN only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models.user import User
from app.schemas.cooperative import CooperativeResponse, CooperativeStatsResponse
from app.services.cooperative import ensure_demo_cooperative, get_cooperative_stats

router = APIRouter(prefix="/cooperative", tags=["cooperative"])


@router.get(
    "/me",
    response_model=CooperativeResponse,
    summary="Get cooperative information (ADMIN only)",
)
def get_cooperative_info(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Return the primary cooperative record for the platform.
    Ensures cooperative existence and links current admin.
    Requires ADMIN authorization.
    """
    coop = ensure_demo_cooperative(db, admin_id=current_user.id)
    return CooperativeResponse.model_validate(coop)


@router.get(
    "/stats",
    response_model=CooperativeStatsResponse,
    summary="Get live cooperative workforce statistics (ADMIN only)",
)
def get_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Calculate and return live workforce statistics (total, verified, pending, rejected, available, unavailable).
    Requires ADMIN authorization.
    """
    return get_cooperative_stats(db)

from app.schemas.cooperative import AnalyticsResponse
from app.services.cooperative import get_cooperative_analytics

@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get analytics data (ADMIN only)",
)
def get_analytics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return get_cooperative_analytics(db)
