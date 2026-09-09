"""
Worker routes — /api/workers

Endpoints:
    GET    /api/workers/me             — get own profile (WORKER)
    POST   /api/workers/me             — create own profile (WORKER)
    PUT    /api/workers/me             — update own profile (WORKER)
    GET    /api/workers/{id}           — get any worker by id (WORKER or ADMIN)
    GET    /api/workers                — list all workers (ADMIN)
    PATCH  /api/workers/{id}/verification — update verification status (ADMIN only)

Route handlers are thin — all business logic is in services/worker.py.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_current_user,
    require_admin,
    require_worker,
)
from app.database.session import get_db
from app.models.user import User
from app.schemas.worker import (
    VerificationUpdateRequest,
    WorkerCreateRequest,
    WorkerResponse,
    WorkerUpdateRequest,
)
from app.services.worker import (
    build_worker_response,
    create_worker_profile,
    get_all_workers,
    get_worker_by_id,
    get_worker_by_user_id,
    update_verification_status,
    update_worker_profile,
)

router = APIRouter(prefix="/workers", tags=["workers"])


# ── GET /api/workers/me ────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=WorkerResponse,
    summary="Get the authenticated worker's own profile",
)
def get_my_profile(
    current_user: User = Depends(require_worker),
    db: Session = Depends(get_db),
):
    """
    Return the currently authenticated worker's profile.
    Returns 404 if no profile has been created yet.
    """
    worker = get_worker_by_user_id(db, current_user.id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker profile not found. Please create your profile.",
        )
    return build_worker_response(worker)


# ── POST /api/workers/me ───────────────────────────────────────────────────────

@router.post(
    "/me",
    response_model=WorkerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create the authenticated worker's profile",
)
def create_my_profile(
    data: WorkerCreateRequest,
    current_user: User = Depends(require_worker),
    db: Session = Depends(get_db),
):
    """
    Create a new worker profile for the authenticated WORKER user.
    Returns 409 if a profile already exists.
    """
    try:
        worker = create_worker_profile(db, current_user.id, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    # Refresh relationship so build_worker_response can access worker.user
    db.refresh(worker)
    return build_worker_response(worker)


# ── PUT /api/workers/me ────────────────────────────────────────────────────────

@router.put(
    "/me",
    response_model=WorkerResponse,
    summary="Update the authenticated worker's profile",
)
def update_my_profile(
    data: WorkerUpdateRequest,
    current_user: User = Depends(require_worker),
    db: Session = Depends(get_db),
):
    """
    Partially update the authenticated worker's profile.
    Only fields present in the request body are updated.
    Protected fields (verification_status, rating, total_jobs) cannot be changed.
    Returns 404 if no profile exists yet.
    """
    worker = get_worker_by_user_id(db, current_user.id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker profile not found. Create your profile first.",
        )
    worker = update_worker_profile(db, worker, data)
    return build_worker_response(worker)


# ── GET /api/workers/{id} ──────────────────────────────────────────────────────

@router.get(
    "/{worker_id}",
    response_model=WorkerResponse,
    summary="Get a worker profile by ID",
)
def get_worker(
    worker_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return any worker's profile by primary key.
    Accessible by authenticated users (WORKER, ADMIN, CUSTOMER).
    Phone number is included — only safe fields are in WorkerResponse.
    """
    worker = get_worker_by_id(db, worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )
    return build_worker_response(worker)


# ── GET /api/workers ───────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[WorkerResponse],
    summary="List all worker profiles (ADMIN only)",
)
def list_workers(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return all worker profiles. ADMIN only."""
    workers = get_all_workers(db)
    return [build_worker_response(w) for w in workers]


# ── PATCH /api/workers/{id}/verification ──────────────────────────────────────

@router.patch(
    "/{worker_id}/verification",
    response_model=WorkerResponse,
    summary="Update a worker's verification status (ADMIN only)",
)
def update_worker_verification(
    worker_id: int,
    data: VerificationUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Change verification_status of a worker profile.

    Allowed statuses: PENDING, VERIFIED, REJECTED.
    Only ADMIN role can call this endpoint — Workers receive 403.
    """
    worker = get_worker_by_id(db, worker_id)
    if not worker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Worker not found",
        )
    worker = update_verification_status(db, worker, data.status)
    return build_worker_response(worker)
