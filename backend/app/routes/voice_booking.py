"""
Voice Booking Route — Sahakar Sathi.

Patent Feature: Zero-Screen-Touch Voice Booking Dispatch.

Customer speaks Hindi → frontend extracts intent → POST /api/voice-booking
→ backend matches best available worker → sends Hindi SMS via Textbelt/Android GW
→ worker replies 1/2 via basic keypad phone → booking confirmed.

Endpoints:
  POST /api/voice-booking             — create voice booking, dispatch Hindi SMS
  POST /api/voice-booking/fallback    — reassign to next worker if declined
  GET  /api/voice-booking/{id}/status — poll booking status
"""
import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_customer
from app.auth.rate_limiter import check_rate_limit, get_client_ip
from app.database.session import get_db
from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.service_request import ServiceRequest, RequestStatus
from app.models.user import User
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.sms_service import (
    build_hindi_job_sms,
    send_sms,
)

logger = logging.getLogger(__name__)

voice_booking_router = APIRouter(tags=["Voice Booking"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class VoiceBookingRequest(BaseModel):
    """Payload from the frontend after voice intent extraction."""
    service_type: str          # e.g. "Electrician", "Plumber"
    urgency: str = "NORMAL"    # "URGENT" | "NORMAL"
    location: str = "Customer Location"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: str = "Voice booking via Sahakar Sathi app"


class VoiceBookingResponse(BaseModel):
    booking_id: int
    worker_name: str
    worker_phone_last4: str
    service_name: str
    sms_sent: bool
    sms_message: str
    scheduled_date: str
    scheduled_time: str
    message: str


class FallbackRequest(BaseModel):
    booking_id: int
    reason: str = "Worker declined"


class BookingStatusResponse(BaseModel):
    booking_id: int
    status: str
    worker_name: str
    service_name: str
    sms_sent: bool


# ---------------------------------------------------------------------------
# Helper: worker scoring for voice dispatch
# ---------------------------------------------------------------------------

def _score_worker(worker: Worker, lat: Optional[float], lon: Optional[float]) -> float:
    """
    Simple scoring: rating (0-5) + proximity bonus + recency penalty.
    Higher = better.
    """
    score = worker.rating * 10  # 0–50

    # Proximity bonus (if coordinates available)
    if lat and lon and worker.latitude and worker.longitude:
        dist = ((lat - worker.latitude) ** 2 + (lon - worker.longitude) ** 2) ** 0.5
        # Rough degree-to-km: 1 degree ≈ 111 km
        dist_km = dist * 111
        if dist_km < 2:
            score += 20
        elif dist_km < 5:
            score += 10
        elif dist_km < 10:
            score += 5

    # Fewer active jobs = more available
    active = getattr(worker, "total_jobs", 0)
    score -= min(active, 10)  # small penalty for very busy workers

    # Peer consensus bonus
    peer_score = getattr(worker, "peer_consensus_score", 0) or 0
    score += peer_score * 5

    return score


def _find_matching_service(db: Session, service_type: str) -> Optional[Service]:
    """Case-insensitive substring match on service name or category."""
    keyword = service_type.strip().lower()
    services = db.query(Service).filter(Service.is_active == True).all()
    # Exact name match first
    for svc in services:
        if keyword in svc.name.lower():
            return svc
    # Category match
    for svc in services:
        if keyword in svc.category.lower():
            return svc
    return None


def _find_available_workers(db: Session, service_type: str, exclude_ids: list[int] = None) -> list[Worker]:
    """
    Get AVAILABLE + VERIFIED workers whose profession or skills match service_type.
    """
    exclude_ids = exclude_ids or []
    keyword = service_type.strip().lower()

    workers = (
        db.query(Worker)
        .filter(
            Worker.availability == AvailabilityStatus.AVAILABLE,
            Worker.verification_status == VerificationStatus.VERIFIED,
            Worker.id.notin_(exclude_ids),
        )
        .all()
    )

    # Filter by profession or skills matching keyword
    matched = []
    for w in workers:
        profession = (w.profession or "").lower()
        skills = [s.lower() for s in (w.skills or [])]

        if (
            keyword in profession
            or any(keyword in sk for sk in skills)
            or any(sk in keyword for sk in skills)
            # Broad fallback: always include if no profession info (fallback pool)
        ):
            matched.append(w)

    # If no exact match, return all available workers (broad fallback)
    if not matched:
        matched = workers

    return matched


def _dispatch_sms_to_worker(worker: Worker, service_name: str, customer_name: str,
                              location: str, scheduled_date: str, scheduled_time: str,
                              booking_id: int) -> tuple[bool, str]:
    """Build and send Hindi SMS to worker. Returns (sms_sent, message)."""
    phone = worker.user.phone if worker.user else None
    if not phone:
        logger.warning("Worker %s has no phone number — skipping SMS", worker.id)
        return False, ""

    msg = build_hindi_job_sms(
        service_name=service_name,
        customer_name=customer_name,
        location=location,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        booking_id=booking_id,
    )

    result = send_sms(phone, msg)
    return result.get("success", False), msg


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@voice_booking_router.post(
    "/voice-booking",
    response_model=VoiceBookingResponse,
    summary="Create a voice-initiated booking and dispatch Hindi SMS to matched worker",
)
def create_voice_booking(
    request: Request,
    payload: VoiceBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Patent Feature: Zero-Screen-Touch Voice Dispatch.

    1. Match service from DB by keyword
    2. Rank available+verified workers
    3. Create ServiceRequest + Booking
    4. Send Hindi SMS to top worker
    5. Return booking details + SMS status
    """
    check_rate_limit(f"{get_client_ip(request)}:{current_user.id}", "voice_booking", max_requests=10, window_seconds=60)
    # 1. Match service
    service = _find_matching_service(db, payload.service_type)
    if not service:
        # Create a generic service entry on the fly for flexibility
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No service found matching '{payload.service_type}'. "
                   "Available: Electrician, Plumber, Cleaner, Carpenter, AC Repair, Painter."
        )

    # 2. Find + rank workers
    workers = _find_available_workers(db, payload.service_type)
    if not workers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No available workers found at the moment. Please try again later.",
        )

    scored = sorted(workers, key=lambda w: _score_worker(w, payload.latitude, payload.longitude), reverse=True)
    best_worker = scored[0]

    # 3. Get cooperative_id (use the worker's cooperative)
    cooperative_id = best_worker.cooperative_id

    # 4. Build schedule (today + ASAP time)
    today = date.today().isoformat()
    time_now = datetime.now().strftime("%H:%M")
    if payload.urgency == "URGENT":
        scheduled_time = time_now
        scheduled_date = today
    else:
        # Schedule for same day or next available slot (simplified: +1 hour)
        hr = datetime.now().hour + 1
        scheduled_time = f"{hr:02d}:00"
        scheduled_date = today

    # 5. Create ServiceRequest
    service_request = ServiceRequest(
        customer_id=current_user.id,
        service_id=service.id,
        cooperative_id=cooperative_id,
        description=payload.description,
        location=payload.location,
        latitude=payload.latitude,
        longitude=payload.longitude,
        preferred_date=scheduled_date,
        preferred_time=scheduled_time,
        status=RequestStatus.ACCEPTED,  # auto-accepted via voice dispatch
    )
    db.add(service_request)
    db.flush()  # get service_request.id

    # 6. Create Booking (assigned_by = customer themselves for voice dispatch)
    booking = Booking(
        request_id=service_request.id,
        worker_id=best_worker.id,
        assigned_by=current_user.id,
        status=BookingStatus.ASSIGNED,
        amount=service.price,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        notes=f"[VOICE BOOKING] {payload.urgency} | {payload.description}",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # 7. Dispatch Hindi SMS
    sms_sent, sms_message = _dispatch_sms_to_worker(
        worker=best_worker,
        service_name=service.name,
        customer_name=current_user.name,
        location=payload.location,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        booking_id=booking.id,
    )

    logger.info(
        "Voice booking created: booking_id=%s worker=%s sms_sent=%s",
        booking.id, best_worker.id, sms_sent
    )

    phone = best_worker.user.phone if best_worker.user else "0000"
    return VoiceBookingResponse(
        booking_id=booking.id,
        worker_name=best_worker.user.name if best_worker.user else "Worker",
        worker_phone_last4=phone[-4:] if phone else "****",
        service_name=service.name,
        sms_sent=sms_sent,
        sms_message=sms_message,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        message=(
            f"✅ बुकिंग हो गई! {service.name} के लिए "
            f"{best_worker.user.name if best_worker.user else 'कारीगर'} को SMS भेज दिया।"
        ),
    )


@voice_booking_router.post(
    "/voice-booking/fallback",
    response_model=VoiceBookingResponse,
    summary="Reassign booking to next best worker if the current one declined",
)
def fallback_voice_booking(
    payload: FallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer),
):
    """
    Called when worker declines (reply=2).
    Picks next available worker and re-dispatches Hindi SMS.
    """
    # Get original booking
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Verify customer owns this booking
    if booking.service_request.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")

    # Mark current as REJECTED
    booking.status = BookingStatus.REJECTED
    db.commit()

    # Find excluded workers (already tried)
    excluded = [booking.worker_id]
    service = booking.service_request.service
    service_type = service.category if service else "general"

    workers = _find_available_workers(db, service_type, exclude_ids=excluded)
    if not workers:
        raise HTTPException(
            status_code=503,
            detail="सभी कारीगर व्यस्त हैं। कृपया कुछ देर बाद प्रयास करें।",
        )

    # Score and pick next best
    lat = booking.service_request.latitude
    lon = booking.service_request.longitude
    scored = sorted(workers, key=lambda w: _score_worker(w, lat, lon), reverse=True)
    next_worker = scored[0]

    # Create new booking for next worker
    new_booking = Booking(
        request_id=booking.request_id,
        worker_id=next_worker.id,
        assigned_by=current_user.id,
        status=BookingStatus.ASSIGNED,
        amount=booking.amount,
        scheduled_date=booking.scheduled_date,
        scheduled_time=booking.scheduled_time,
        notes=f"[VOICE FALLBACK from #{booking.id}] {payload.reason}",
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    sms_sent, sms_message = _dispatch_sms_to_worker(
        worker=next_worker,
        service_name=service.name if service else service_type,
        customer_name=current_user.name,
        location=booking.service_request.location,
        scheduled_date=new_booking.scheduled_date,
        scheduled_time=new_booking.scheduled_time,
        booking_id=new_booking.id,
    )

    phone = next_worker.user.phone if next_worker.user else "0000"
    return VoiceBookingResponse(
        booking_id=new_booking.id,
        worker_name=next_worker.user.name if next_worker.user else "Worker",
        worker_phone_last4=phone[-4:] if phone else "****",
        service_name=service.name if service else service_type,
        sms_sent=sms_sent,
        sms_message=sms_message,
        scheduled_date=new_booking.scheduled_date,
        scheduled_time=new_booking.scheduled_time,
        message=(
            f"♻️ दूसरे कारीगर को SMS भेज दिया। "
            f"{next_worker.user.name if next_worker.user else 'नए कारीगर'} से जल्द जवाब आएगा।"
        ),
    )


@voice_booking_router.get(
    "/voice-booking/{booking_id}/status",
    response_model=BookingStatusResponse,
    summary="Poll the status of a voice booking",
)
def get_voice_booking_status(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Status polling endpoint — frontend polls this after SMS dispatch."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    worker = booking.worker
    service = booking.service_request.service if booking.service_request else None

    return BookingStatusResponse(
        booking_id=booking.id,
        status=booking.status.value,
        worker_name=worker.user.name if worker and worker.user else "Worker",
        service_name=service.name if service else "Service",
        sms_sent=True,
    )
