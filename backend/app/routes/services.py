"""
Service catalog routes — /api/services

Endpoints:
    GET  /api/services  — list all active services in the catalog (Authenticated)
    POST /api/services  — add new service to catalog (ADMIN only)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database.session import get_db
from app.models.user import User
from app.schemas.service import ServiceCreateRequest, ServiceResponse
from app.services.service_catalog import (
    create_service,
    ensure_seed_services,
    get_all_services,
)

router = APIRouter(prefix="/services", tags=["services"])


@router.get(
    "",
    response_model=List[ServiceResponse],
    summary="List available services in the catalog",
)
def list_services(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all active services in the catalog.
    Seeds default services if the catalog is empty.
    Accessible by any authenticated user (Customer, Worker, Admin).
    """
    services = get_all_services(db, active_only=True)
    if not services:
        services = ensure_seed_services(db)
    return [ServiceResponse.model_validate(s) for s in services]


@router.post(
    "",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new service to the catalog (ADMIN only)",
)
def add_service(
    data: ServiceCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new service entry in the cooperative catalog.
    Requires ADMIN authorization.
    """
    try:
        service = create_service(db, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    return ServiceResponse.model_validate(service)
