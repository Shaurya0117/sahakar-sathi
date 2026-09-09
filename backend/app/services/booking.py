"""
Booking Service Layer.

Handles worker allocation, status transitions, conflict protection, authorization,
and atomic total_jobs updates for cooperative workload fairness.
"""
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.schemas.booking import BookingResponse
from app.services.matching.candidate_filter import is_profession_or_skill_relevant

ACTIVE_BOOKING_STATUSES = [BookingStatus.ASSIGNED, BookingStatus.ACCEPTED, BookingStatus.IN_PROGRESS]


def can_transition_booking_status(current_status: BookingStatus, target_status: BookingStatus) -> bool:
    """
    Validate explicit allowed status transitions:
        ASSIGNED -> ACCEPTED | REJECTED
        ACCEPTED -> IN_PROGRESS
        IN_PROGRESS -> COMPLETED
    """
    allowed_map = {
        BookingStatus.ASSIGNED: {BookingStatus.ACCEPTED, BookingStatus.REJECTED},
        BookingStatus.ACCEPTED: {BookingStatus.IN_PROGRESS},
        BookingStatus.IN_PROGRESS: {BookingStatus.COMPLETED},
    }
    return target_status in allowed_map.get(current_status, set())


def build_booking_response(db: Session, booking: Booking) -> BookingResponse:
    """Enrich a Booking ORM instance with customer, worker, service, and assigner details."""
    worker = db.query(Worker).filter(Worker.id == booking.worker_id).first()
    worker_user = db.query(User).filter(User.id == worker.user_id).first() if worker else None

    req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
    customer_user = db.query(User).filter(User.id == req.customer_id).first() if req else None
    service = db.query(Service).filter(Service.id == req.service_id).first() if req else None

    assigner = db.query(User).filter(User.id == booking.assigned_by).first()

    return BookingResponse(
        id=booking.id,
        request_id=booking.request_id,
        worker_id=booking.worker_id,
        worker_name=worker_user.name if worker_user else f"Worker #{booking.worker_id}",
        worker_phone=worker_user.phone if worker_user else None,
        customer_id=req.customer_id if req else 0,
        customer_name=customer_user.name if customer_user else "Customer",
        customer_phone=customer_user.phone if customer_user else None,
        service_name=service.name if service else "Service",
        service_category=service.category if service else "Household",
        location=req.location if req else "",
        scheduled_date=booking.scheduled_date,
        scheduled_time=booking.scheduled_time,
        image_url=req.image_url if req else None,
        status=booking.status.value if hasattr(booking.status, 'value') else str(booking.status),
        amount=booking.amount,
        customer_rating=booking.customer_rating,
        customer_review=booking.customer_review,
        proof_of_work_hash=booking.proof_of_work_hash,
        privacy_score=booking.privacy_score,
        payment_status=booking.payment_status or "PENDING",
        assigned_by_name=assigner.name if assigner else "Cooperative Admin",
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )


def allocate_worker_to_request(
    db: Session,
    request_id: int,
    admin_user: User,
    worker_id: int,
    amount: Optional[float] = None,
) -> BookingResponse:
    """
    Allocate a verified worker to a pending service request (ADMIN ONLY).
    """
    # 1. Validate request exists
    req = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found.")

    # 1b. Validate request belongs to admin's cooperative
    admin_coop = db.query(Cooperative).filter(Cooperative.admin_id == admin_user.id).first()
    if admin_coop and req.cooperative_id and req.cooperative_id != admin_coop.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot allocate requests belonging to another cooperative.",
        )

    # 2. Validate request status is PENDING
    if req.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Service request cannot be allocated because its status is {req.status.value}.",
        )

    # 3. Validate no active booking exists for request
    existing_active_booking = db.query(Booking).filter(
        Booking.request_id == request_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
    ).first()
    if existing_active_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active booking already exists for this service request.",
        )

    # 4. Validate worker exists
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker profile not found.")

    # 5. Validate cooperative pool
    if req.cooperative_id and worker.cooperative_id and worker.cooperative_id != req.cooperative_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker does not belong to the cooperative associated with this request.",
        )

    # 6. Validate worker verification status
    if worker.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker is not verified by the cooperative.",
        )

    # 7. Validate worker availability
    if worker.availability != AvailabilityStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker is currently set to UNAVAILABLE.",
        )

    # 8. Validate skill relevance
    service = db.query(Service).filter(Service.id == req.service_id).first()
    if service and not is_profession_or_skill_relevant(service, worker):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worker profession/skills are not relevant to requested service.",
        )

    # 9. Conflict Protection: Worker date/time conflict check
    schedule_conflict = db.query(Booking).filter(
        Booking.worker_id == worker_id,
        Booking.scheduled_date == req.preferred_date,
        Booking.scheduled_time == req.preferred_time,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
    ).first()
    if schedule_conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Worker already has an active job scheduled at {req.preferred_date} {req.preferred_time}.",
        )

    # All validations passed -> Update Request & Create Booking
    req.status = RequestStatus.ACCEPTED
    booking = Booking(
        request_id=req.id,
        worker_id=worker.id,
        assigned_by=admin_user.id,
        status=BookingStatus.ASSIGNED,
        amount=amount,
        scheduled_date=req.preferred_date,
        scheduled_time=req.preferred_time,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return build_booking_response(db, booking)


def get_worker_bookings(db: Session, worker_user: User) -> List[BookingResponse]:
    """Get all bookings assigned to the current authenticated worker."""
    worker = db.query(Worker).filter(Worker.user_id == worker_user.id).first()
    if not worker:
        return []

    bookings = db.query(Booking).filter(Booking.worker_id == worker.id).order_by(Booking.created_at.desc()).all()
    return [build_booking_response(db, b) for b in bookings]


def get_customer_bookings(db: Session, customer_user: User) -> List[BookingResponse]:
    """Get all bookings for requests owned by the current authenticated customer."""
    bookings = db.query(Booking).join(ServiceRequest).filter(
        ServiceRequest.customer_id == customer_user.id
    ).order_by(Booking.created_at.desc()).all()
    return [build_booking_response(db, b) for b in bookings]


def get_cooperative_bookings(db: Session, admin_user: User) -> List[BookingResponse]:
    """Get all bookings for requests under the admin's cooperative."""
    coop = db.query(Cooperative).filter(Cooperative.admin_id == admin_user.id).first()
    query = db.query(Booking).join(ServiceRequest)
    if coop:
        query = query.filter(ServiceRequest.cooperative_id == coop.id)

    bookings = query.order_by(Booking.created_at.desc()).all()
    return [build_booking_response(db, b) for b in bookings]


def get_booking_by_id(db: Session, booking_id: int, current_user: User) -> BookingResponse:
    """Get single booking details with participant authorization check."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()

    # Participant check
    is_customer = req and req.customer_id == current_user.id
    is_worker = False
    if current_user.role == UserRole.WORKER and current_user.worker_profile:
        is_worker = booking.worker_id == current_user.worker_profile.id

    is_admin = current_user.role == UserRole.ADMIN

    if not (is_customer or is_worker or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this booking.")

    return build_booking_response(db, booking)


def accept_booking(db: Session, booking_id: int, worker_user: User) -> BookingResponse:
    """Worker accepts assigned job (ASSIGNED -> ACCEPTED)."""
    worker = db.query(Worker).filter(Worker.user_id == worker_user.id).first()
    if not worker:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Worker profile not found.")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    if booking.worker_id != worker.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own assigned jobs.")

    if not can_transition_booking_status(booking.status, BookingStatus.ACCEPTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition booking from {booking.status.value} to ACCEPTED.",
        )

    booking.status = BookingStatus.ACCEPTED
    db.commit()
    db.refresh(booking)
    return build_booking_response(db, booking)


def reject_booking(db: Session, booking_id: int, worker_user: User) -> BookingResponse:
    """
    Worker rejects assigned job (ASSIGNED -> REJECTED).
    Resets the underlying ServiceRequest back to PENDING so Admin can re-allocate.
    """
    worker = db.query(Worker).filter(Worker.user_id == worker_user.id).first()
    if not worker:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Worker profile not found.")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    if booking.worker_id != worker.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own assigned jobs.")

    if not can_transition_booking_status(booking.status, BookingStatus.REJECTED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition booking from {booking.status.value} to REJECTED.",
        )

    booking.status = BookingStatus.REJECTED

    # Reset ServiceRequest to PENDING
    req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
    if req:
        req.status = RequestStatus.PENDING

    db.commit()
    db.refresh(booking)
    return build_booking_response(db, booking)


def start_booking(db: Session, booking_id: int, worker_user: User) -> BookingResponse:
    """Worker starts service (ACCEPTED -> IN_PROGRESS)."""
    worker = db.query(Worker).filter(Worker.user_id == worker_user.id).first()
    if not worker:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Worker profile not found.")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    if booking.worker_id != worker.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own assigned jobs.")

    if not can_transition_booking_status(booking.status, BookingStatus.IN_PROGRESS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition booking from {booking.status.value} to IN_PROGRESS.",
        )

    booking.status = BookingStatus.IN_PROGRESS
    db.commit()
    db.refresh(booking)
    return build_booking_response(db, booking)


from app.schemas.booking import CompleteBookingRequest

def complete_booking(db: Session, booking_id: int, worker_user: User, payload: Optional[CompleteBookingRequest] = None) -> BookingResponse:
    """
    Worker marks service completed (IN_PROGRESS -> COMPLETED).
    Updates Booking & ServiceRequest to COMPLETED, and atomically increments worker.total_jobs.
    Now supports Privacy-Preserving Proof of Work (Edge AI).
    """
    worker = db.query(Worker).filter(Worker.user_id == worker_user.id).first()
    if not worker:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Worker profile not found.")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    if booking.worker_id != worker.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own assigned jobs.")

    if not can_transition_booking_status(booking.status, BookingStatus.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition booking from {booking.status.value} to COMPLETED.",
        )

    booking.status = BookingStatus.COMPLETED
    
    if payload:
        booking.proof_of_work_hash = payload.proof_of_work_hash
        booking.privacy_score = payload.privacy_score

    # Update ServiceRequest to COMPLETED
    req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
    if req:
        req.status = RequestStatus.COMPLETED

    # Atomically increment worker.total_jobs to update future fairness score
    worker.total_jobs = (worker.total_jobs or 0) + 1

    db.commit()
    db.refresh(booking)
    return build_booking_response(db, booking)

from app.schemas.booking import ReviewCreateRequest
from sqlalchemy.sql import func

def submit_booking_review(
    db: Session,
    booking_id: int,
    customer_user: User,
    data: ReviewCreateRequest
) -> BookingResponse:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    req = db.query(ServiceRequest).filter(ServiceRequest.id == booking.request_id).first()
    if not req or req.customer_id != customer_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to review this booking")
        
    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Only COMPLETED bookings can be reviewed")
        
    if booking.customer_rating is not None:
        raise HTTPException(status_code=400, detail="Booking already reviewed")
        
    booking.customer_rating = data.rating
    booking.customer_review = data.review
    db.commit()
    
    # Recalculate worker average rating
    worker = db.query(Worker).filter(Worker.id == booking.worker_id).first()
    if worker:
        avg_rating = db.query(func.avg(Booking.customer_rating)).filter(Booking.worker_id == worker.id, Booking.customer_rating.isnot(None)).scalar()
        worker.rating = float(avg_rating) if avg_rating else 0.0
        db.commit()
        
    db.refresh(booking)
    return build_booking_response(db, booking)
