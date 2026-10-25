"""
FastAPI route handlers for Worker Allocation and Booking Lifecycle.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, status, Body, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin, require_customer, require_worker
from app.database.session import get_db
from app.models.user import User
from app.models.booking import Booking, BookingStatus
from app.models.service_request import ServiceRequest
from app.services.proof_verification import derive_completion_code
from app.schemas.booking import AllocateWorkerRequest, BookingResponse, CompleteBookingRequest
from app.services.booking import (
    accept_booking,
    allocate_worker_to_request,
    complete_booking,
    get_booking_by_id,
    get_booking_started_at_iso,
    get_cooperative_bookings,
    get_customer_bookings,
    get_worker_bookings,
    reject_booking,
    start_booking,
)

bookings_router = APIRouter(tags=["Bookings"])


@bookings_router.post(
    "/requests/{request_id}/allocate",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate a verified worker to a service request (ADMIN only)",
)
def allocate_worker(
    request_id: int,
    payload: AllocateWorkerRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Allocate a worker to a pending request, creating a Booking record in ASSIGNED status.
    Only accessible by Cooperative Admin.
    """
    return allocate_worker_to_request(
        db=db,
        request_id=request_id,
        admin_user=admin_user,
        worker_id=payload.worker_id,
        amount=payload.amount,
    )


@bookings_router.get(
    "/bookings/worker",
    response_model=List[BookingResponse],
    summary="Get all assigned jobs for current worker (WORKER only)",
)
def get_my_worker_jobs(
    db: Session = Depends(get_db),
    worker_user: User = Depends(require_worker),
):
    return get_worker_bookings(db, worker_user)


@bookings_router.get(
    "/bookings/me",
    response_model=List[BookingResponse],
    summary="Get all bookings for current customer (CUSTOMER only)",
)
def get_my_customer_bookings(
    db: Session = Depends(get_db),
    customer_user: User = Depends(require_customer),
):
    return get_customer_bookings(db, customer_user)


@bookings_router.get(
    "/bookings",
    response_model=List[BookingResponse],
    summary="Get all cooperative bookings (ADMIN only)",
)
def get_all_cooperative_bookings(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    return get_cooperative_bookings(db, admin_user)


@bookings_router.get(
    "/bookings/{id}",
    response_model=BookingResponse,
    summary="Get details of a single booking (Authorized participants only)",
)
def get_booking_details(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_booking_by_id(db, id, current_user)


@bookings_router.patch(
    "/bookings/{id}/accept",
    response_model=BookingResponse,
    summary="Accept an assigned job (WORKER only)",
)
def accept_job(
    id: int,
    db: Session = Depends(get_db),
    worker_user: User = Depends(require_worker),
):
    result = accept_booking(db, id, worker_user)
    try:
        from app.ml.bandit import record_outcome
        import datetime as _dt
        from app.models.worker import Worker as _Worker
        booking = db.query(Booking).filter(Booking.id == id).first()
        hour = _dt.datetime.utcnow().hour
        trade = "general"
        if booking and booking.worker_id:
            _w = db.query(_Worker).filter(_Worker.id == booking.worker_id).first()
            trade = _w.profession if _w and _w.profession else "general"
        record_outcome(trade, hour, 0, True)
    except Exception:
        pass
    return result


@bookings_router.patch(
    "/bookings/{id}/reject",
    response_model=BookingResponse,
    summary="Reject an assigned job (WORKER only)",
)
def reject_job(
    id: int,
    db: Session = Depends(get_db),
    worker_user: User = Depends(require_worker),
):
    result = reject_booking(db, id, worker_user)
    try:
        from app.ml.bandit import record_outcome
        import datetime as _dt
        from app.models.worker import Worker as _Worker
        booking = db.query(Booking).filter(Booking.id == id).first()
        hour = _dt.datetime.utcnow().hour
        trade = "general"
        if booking and booking.worker_id:
            _w = db.query(_Worker).filter(_Worker.id == booking.worker_id).first()
            trade = _w.profession if _w and _w.profession else "general"
        record_outcome(trade, hour, 0, False)
    except Exception:
        pass
    return result


@bookings_router.patch(
    "/bookings/{id}/start",
    response_model=BookingResponse,
    summary="Start an accepted service job (WORKER only)",
)
def start_job(
    id: int,
    db: Session = Depends(get_db),
    worker_user: User = Depends(require_worker),
):
    return start_booking(db, id, worker_user)

from app.services.booking import mark_arrived

@bookings_router.patch(
    "/bookings/{id}/arrive",
    response_model=BookingResponse,
    summary="Mark worker as arrived (WORKER only)",
)
def arrive_job(
    id: int,
    db: Session = Depends(get_db),
    worker_user: User = Depends(require_worker),
):
    return mark_arrived(db, id, worker_user)


@bookings_router.patch(
    "/bookings/{id}/complete",
    response_model=BookingResponse,
    summary="Mark a service job completed (WORKER only)",
)
def complete_job(
    id: int,
    payload: Optional[CompleteBookingRequest] = Body(None),
    db: Session = Depends(get_db),
    worker_user: User = Depends(require_worker),
):
    return complete_booking(db, id, worker_user, payload)

from app.schemas.booking import ReviewCreateRequest
from app.services.booking import submit_booking_review
from app.auth.dependencies import require_customer

@bookings_router.post(
    "/bookings/{id}/review",
    response_model=BookingResponse,
    summary="Review a completed service job (CUSTOMER only)",
)
def review_job(
    id: int,
    data: ReviewCreateRequest,
    db: Session = Depends(get_db),
    customer_user: User = Depends(require_customer),
):
    return submit_booking_review(db, id, customer_user, data)


@bookings_router.get(
    "/bookings/{id}/completion-code",
    summary="Get job completion code (CUSTOMER only)",
)
def get_job_completion_code(
    id: int,
    db: Session = Depends(get_db),
    customer_user: User = Depends(require_customer),
):
    booking = db.query(Booking).filter(Booking.id == id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
    if not req or req.customer_id != customer_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access completion code for this booking.")

    if booking.status != BookingStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Completion code is only available when booking is in progress.")

    started_at_iso = get_booking_started_at_iso(booking)
    code = derive_completion_code(booking.id, started_at_iso)
    return {"code": code}
