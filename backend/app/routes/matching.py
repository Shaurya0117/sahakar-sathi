"""
FastAPI route handlers for Explainable Cooperative Worker Matching.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.database.session import get_db
from app.models.user import User
from app.schemas.matching import RequestMatchingResponse
from app.services.matching import get_matching_recommendations

matching_router = APIRouter(prefix="/matching", tags=["Matching"])


@matching_router.get(
    "/requests/{request_id}",
    response_model=RequestMatchingResponse,
    summary="Get explainable worker recommendations for a service request (ADMIN only)",
)
def get_request_matching_recommendations(
    request_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Return ranked worker recommendations with transparent score breakdown
    and explainable match reasons for a specific service request.
    Only accessible by Cooperative Admins.
    """
    return get_matching_recommendations(db, request_id)
