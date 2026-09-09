"""
ServiceRequest route handlers — /api/requests

Endpoints:
    POST   /api/requests            — create a new request (CUSTOMER only)
    GET    /api/requests/me         — list customer's own requests (CUSTOMER only)
    GET    /api/requests/{id}       — get single request detail (CUSTOMER only)
    PATCH  /api/requests/{id}/cancel — cancel a pending request (CUSTOMER only)
    GET    /api/requests            — list all cooperative requests (ADMIN only)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, require_customer
from app.database.session import get_db
from app.models.user import User
from app.schemas.service_request import (
    ServiceRequestCancelResponse,
    ServiceRequestCreateRequest,
    ServiceRequestResponse,
)
from app.services.service_request import (
    build_service_request_response,
    cancel_service_request,
    create_service_request,
    get_all_cooperative_requests_for_admin,
    get_customer_requests,
    get_request_by_id_for_customer,
)

router = APIRouter(prefix="/requests", tags=["service-requests"])


# ── POST /api/requests ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ServiceRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new service request (CUSTOMER only)",
)
def create_request(
    data: ServiceRequestCreateRequest,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Create a new service request for the authenticated CUSTOMER.
    Service must exist and be active.
    Customer ID is derived directly from the JWT.
    """
    try:
        req = create_service_request(db, current_user.id, data)
    except ValueError as exc:
        msg = str(exc)
        if "does not exist" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    return build_service_request_response(req)


# ── GET /api/requests/me ───────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=List[ServiceRequestResponse],
    summary="List the authenticated customer's requests (CUSTOMER only)",
)
def list_my_requests(
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Return all service requests submitted by the authenticated CUSTOMER, newest first.
    """
    requests = get_customer_requests(db, current_user.id)
    return [build_service_request_response(r) for r in requests]


# ── GET /api/requests/{id} ─────────────────────────────────────────────────────

@router.get(
    "/{request_id}",
    response_model=ServiceRequestResponse,
    summary="Get request details by ID (CUSTOMER only)",
)
def get_request_detail(
    request_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Return details of a specific request owned by the authenticated CUSTOMER.
    Returns 404 if not found or owned by another user (does not reveal existence).
    """
    req = get_request_by_id_for_customer(db, request_id, current_user.id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service request not found",
        )
    return build_service_request_response(req)


# ── PATCH /api/requests/{id}/cancel ───────────────────────────────────────────

@router.patch(
    "/{request_id}/cancel",
    response_model=ServiceRequestCancelResponse,
    summary="Cancel a pending request (CUSTOMER only)",
)
def cancel_request(
    request_id: int,
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    """
    Cancel a pending request owned by the authenticated CUSTOMER.
    Allowed ONLY when status is PENDING.
    """
    try:
        req = cancel_service_request(db, request_id, current_user.id)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )
    return ServiceRequestCancelResponse(
        message="Service request cancelled successfully",
        request=build_service_request_response(req),
    )


# ── GET /api/requests ──────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[ServiceRequestResponse],
    summary="List all cooperative service requests (ADMIN only)",
)
def list_all_requests_admin(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Return all service requests submitted to the cooperative.
    Accessible exclusively by ADMIN users.
    Workers receive 403.
    """
    requests = get_all_cooperative_requests_for_admin(db)
    return [build_service_request_response(r) for r in requests]

# ── POST /api/requests/{id}/upload-photo ───────────────────────────────────────

import os
import shutil
from fastapi import UploadFile, File

@router.post(
    "/{request_id}/upload-photo",
    response_model=ServiceRequestResponse,
    summary="Upload a photo for a service request (CUSTOMER only)",
)
def upload_request_photo(
    request_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    req = get_request_by_id_for_customer(db, request_id, current_user.id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
        
    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = f"{upload_dir}/req_{req.id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    req.image_url = f"/{file_path}"
    db.commit()
    db.refresh(req)
    
    return build_service_request_response(req)
