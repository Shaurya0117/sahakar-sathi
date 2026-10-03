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

import os
import shutil
import uuid
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from app.models.user import UserRole
from app.models.booking import Booking

PRIVATE_UPLOAD_DIR = "private_uploads"

@router.post(
    "/{request_id}/upload-photo",
    response_model=ServiceRequestResponse,
    summary="Upload a photo securely with UUID (CUSTOMER only)",
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
        
    os.makedirs(PRIVATE_UPLOAD_DIR, exist_ok=True)
    
    # Generate UUID filename
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(PRIVATE_UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Store internal path or secure url
    req.image_url = f"/api/requests/{req.id}/photo"
    req.internal_image_path = file_path # Ideally add column, but we can store it in image_url for now
    req.image_url = f"/api/requests/{req.id}/photo?path={safe_filename}"
    db.commit()
    db.refresh(req)
    
    return build_service_request_response(req)

from app.auth.dependencies import get_current_user
@router.get(
    "/{request_id}/photo",
    summary="Serve request photo securely with auth check",
)
def get_request_photo(
    request_id: int,
    path: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    req = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")
        
    # Auth check: Customer owner, Admin, or Assigned Worker
    is_authorized = False
    if current_user.role == UserRole.ADMIN:
        is_authorized = True
    elif current_user.role == UserRole.CUSTOMER and req.customer_id == current_user.id:
        is_authorized = True
    elif current_user.role == UserRole.WORKER:
        # Check if worker is assigned to this request
        worker = current_user.worker_profile
        if worker:
            booking = db.query(Booking).filter(
                Booking.request_id == request_id, 
                Booking.worker_id == worker.id
            ).first()
            if booking:
                is_authorized = True
                
    if not is_authorized:
        raise HTTPException(status_code=403, detail="Not authorized to view this photo.")
        
    file_path = os.path.join(PRIVATE_UPLOAD_DIR, path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Photo file not found.")
        
    return FileResponse(file_path)
