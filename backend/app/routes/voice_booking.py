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
from app.config import settings, MAX_FATIGUE_THRESHOLD
from app.database.session import get_db
from app.models.booking import Booking, BookingStatus
from app.models.service import Service
from app.models.service_request import ServiceRequest, RequestStatus
from app.models.user import User
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.matching.scorer import (
    calculate_availability_score,
    calculate_bio_economic_metrics,
    calculate_experience_score,
    calculate_location_score,
    calculate_rating_score,
    calculate_skill_score,
    calculate_total_score,
)
from app.services.matching.equity_graph import calculate_equity_score
from app.services.sms_service import (
    build_hindi_confirmation_sms,
    build_hindi_fallback_sms,
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
    score = worker.rating * 10
    if lat and lon and worker.latitude and worker.longitude:
        dist = ((lat - worker.latitude) ** 2 + (lon - worker.longitude) ** 2) ** 0.5
        dist_km = dist * 111
        if dist_km < 2:
            score += 20
        elif dist_km < 5:
            score += 10
        elif dist_km < 10:
            score += 5
    active = getattr(worker, "total_jobs", 0)
    score -= min(active, 10)
    peer_score = getattr(worker, "peer_consensus_score", 0) or 0
    score += peer_score * 5
    return score


def score_and_filter_voice_worker(
    worker: Worker,
    service: Service,
    location: str,
    lat: Optional[float],
    lon: Optional[float],
    db: Session,
) -> Optional[float]:
    """
    Score worker using multi-factor bio-economic and equity engine.
    Excludes workers with fatigue >= 80% (Claim c).
    """
    bio_metrics = calculate_bio_economic_metrics(worker, db)
    fatigue_idx = bio_metrics.get("fatigue_index", 0.0)
    if bio_metrics.get("is_fatigued") or fatigue_idx >= MAX_FATIGUE_THRESHOLD:
        logger.info("Worker #%s excluded from voice dispatch: fatigue %.1f >= %.1f", worker.id, fatigue_idx, MAX_FATIGUE_THRESHOLD)
        return None

    equity_data = calculate_equity_score(db, worker)
    if equity_data.get("is_fatigued"):
        logger.info("Worker #%s excluded from voice dispatch: equity marked fatigued", worker.id)
        return None

    skill_score = calculate_skill_score(service, worker)
    location_score = calculate_location_score(
        location,
        worker.location,
        request_lat=lat,
        request_lon=lon,
        worker_lat=getattr(worker, "latitude", None),
        worker_lon=getattr(worker, "longitude", None),
    )
    availability_score = calculate_availability_score(worker)
    rating_score = calculate_rating_score(worker)
    experience_score = calculate_experience_score(worker)

    breakdown = {
        "skill_match": skill_score,
        "location": location_score,
        "availability": availability_score,
        "rating": rating_score,
        "experience": experience_score,
        "equity_score": equity_data.get("composite_equity_score", 50.0),
        "workload_fairness": bio_metrics,
    }
    return calculate_total_score(breakdown)


def select_best_voice_worker(
    db: Session,
    service: Service,
    location: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    exclude_worker_ids: Optional[list] = None,
) -> Optional[Worker]:
    """
    Find and return highest-scoring eligible worker for a voice booking.
    Excludes previously attempted workers and workers with fatigue >= 80%.
    """
    exclude_ids = set(exclude_worker_ids or [])
    service_type = service.category or service.name
    candidates = _find_available_workers(db, service_type, exclude_ids=list(exclude_ids))

    scored_workers = []
    for w in candidates:
        if w.id in exclude_ids:
            continue
        score = score_and_filter_voice_worker(w, service, location, lat, lon, db)
        if score is not None:
            scored_workers.append((score, w))

    if not scored_workers:
        return None

    scored_workers.sort(key=lambda item: (item[0], -item[1].id), reverse=True)
    return scored_workers[0][1]


def dispatch_to_next_worker(
    db: Session,
    request_id: int,
    current_booking_id: int,
    reason: str = "DECLINED",
) -> tuple:
    """
    Auto re-dispatches voice booking to the next best worker.
    - Excludes all previously attempted workers for this request.
    - Uses same fatigue- and equity-aware scorer (fatigue >= 80% excluded).
    - Enforces MAX_DISPATCH_ATTEMPTS: if reached, marks UNASSIGNED and notifies customer.
    """
    current_booking = db.query(Booking).filter(Booking.id == current_booking_id).first()
    if not current_booking:
        return None, None, False, "Original booking not found"

    all_bookings = (
        db.query(Booking)
        .filter(Booking.request_id == request_id)
        .order_by(Booking.created_at.asc())
        .all()
    )
    attempt_count = len(all_bookings)
    max_attempts = getattr(settings, "MAX_DISPATCH_ATTEMPTS", 3)

    service_request = current_booking.service_request
    service = service_request.service if service_request else None
    customer = service_request.customer if service_request else None
    customer_phone = customer.phone if customer else None

    if attempt_count >= max_attempts:
        current_booking.status = BookingStatus.UNASSIGNED
        current_booking.notes = f"{current_booking.notes or ''} [MAX_ATTEMPTS_REACHED_{attempt_count}]"
        if service_request:
            service_request.status = RequestStatus.PENDING
        db.commit()

        if customer_phone:
            notice = "क्षमा करें, कोई कारीगर उपलब्ध नहीं हो सका। कृपया बाद में प्रयास करें।"
            send_sms(customer_phone, notice)

        logger.info("Booking #%s reached MAX_DISPATCH_ATTEMPTS (%d/%d). Set to UNASSIGNED.", current_booking.id, attempt_count, max_attempts)
        return None, None, False, f"Maximum dispatch attempts ({max_attempts}) reached. Booking marked UNASSIGNED."

    excluded_ids = [b.worker_id for b in all_bookings]

    next_worker = select_best_voice_worker(
        db=db,
        service=service,
        location=service_request.location if service_request else "Customer Location",
        lat=service_request.latitude if service_request else None,
        lon=service_request.longitude if service_request else None,
        exclude_worker_ids=excluded_ids,
    )

    if not next_worker:
        current_booking.status = BookingStatus.UNASSIGNED
        current_booking.notes = f"{current_booking.notes or ''} [NO_ELIGIBLE_WORKERS]"
        if service_request:
            service_request.status = RequestStatus.PENDING
        db.commit()

        if customer_phone:
            notice = "क्षमा करें, कोई कारीगर उपलब्ध नहीं हो सका। कृपया बाद में प्रयास करें।"
            send_sms(customer_phone, notice)

        logger.info("No further eligible non-fatigued workers for request #%s. Marked UNASSIGNED.", request_id)
        return None, None, False, "No further eligible workers available. Booking marked UNASSIGNED."

    new_attempt_num = attempt_count + 1
    new_booking = Booking(
        request_id=request_id,
        worker_id=next_worker.id,
        assigned_by=current_booking.assigned_by,
        status=BookingStatus.ASSIGNED,
        amount=current_booking.amount,
        scheduled_date=current_booking.scheduled_date,
        scheduled_time=current_booking.scheduled_time,
        notes=f"[VOICE BOOKING] Attempt {new_attempt_num}/{max_attempts} | Fallback from #{current_booking_id} ({reason})",
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    sms_sent, sms_message = _dispatch_sms_to_worker(
        worker=next_worker,
        service_name=service.name if service else "Service",
        customer_name=customer.name if customer else "ग्राहक",
        location=service_request.location if service_request else "Customer Location",
        scheduled_date=new_booking.scheduled_date,
        scheduled_time=new_booking.scheduled_time,
        booking_id=new_booking.id,
    )

    logger.info("Auto-reassigned request #%s to Worker #%s (booking #%s, attempt %d/%d)", request_id, next_worker.id, new_booking.id, new_attempt_num, max_attempts)
    return new_booking, next_worker, sms_sent, sms_message


def process_voice_booking_timeouts(db: Session) -> list:
    """
    Check for voice bookings in ASSIGNED status where worker has not replied
    within SMS_REPLY_TIMEOUT_MINUTES. Auto-expires offer and reassigns to next worker.
    """
    timeout_mins = getattr(settings, "SMS_REPLY_TIMEOUT_MINUTES", 10)
    now = datetime.utcnow()

    assigned_bookings = (
        db.query(Booking)
        .filter(Booking.status == BookingStatus.ASSIGNED)
        .all()
    )

    results = []
    for b in assigned_bookings:
        if not (b.notes and "[VOICE BOOKING]" in b.notes):
            continue

        created_time = b.created_at if hasattr(b, "created_at") and b.created_at else None
        if not created_time:
            continue

        elapsed_mins = (now - created_time).total_seconds() / 60.0
        if elapsed_mins >= timeout_mins:
            logger.info("Booking #%s timed out after %.1f mins (limit %d mins)", b.id, elapsed_mins, timeout_mins)
            b.status = BookingStatus.REJECTED
            b.notes = f"{b.notes or ''} [EXPIRED_TIMEOUT]"
            db.commit()

            if b.worker and b.worker.user and b.worker.user.phone:
                msg = build_hindi_fallback_sms(b.id)
                send_sms(b.worker.user.phone, msg)

            new_b, next_w, sms_sent, msg = dispatch_to_next_worker(
                db=db,
                request_id=b.request_id,
                current_booking_id=b.id,
                reason="TIMEOUT",
            )
            results.append({
                "expired_booking_id": b.id,
                "reassigned_booking_id": new_b.id if new_b else None,
                "next_worker_id": next_w.id if next_w else None,
                "sms_sent": sms_sent,
                "message": msg,
            })
    return results


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
    if isinstance(result, dict):
        sent = result.get("success", False)
    elif isinstance(result, bool):
        sent = result
    else:
        sent = bool(result)
    return sent, msg


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

    # 2. Select best eligible worker using fatigue- and equity-aware scorer (excludes >= 80% fatigue)
    best_worker = select_best_voice_worker(
        db=db,
        service=service,
        location=payload.location,
        lat=payload.latitude,
        lon=payload.longitude,
    )
    if not best_worker:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No available non-fatigued workers found at the moment. Please try again later.",
        )

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
        notes=f"[VOICE BOOKING] Attempt 1/{getattr(settings, 'MAX_DISPATCH_ATTEMPTS', 3)} | {payload.urgency} | {payload.description}",
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
    Picks next available worker using the same fatigue/equity-aware scorer and re-dispatches Hindi SMS.
    """
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.service_request.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your booking")

    booking.status = BookingStatus.REJECTED
    booking.notes = f"{booking.notes or ''} [FALLBACK_REQUESTED: {payload.reason}]"
    db.commit()

    new_booking, next_worker, sms_sent, sms_message = dispatch_to_next_worker(
        db=db,
        request_id=booking.request_id,
        current_booking_id=booking.id,
        reason=payload.reason,
    )

    if not new_booking or not next_worker:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="सभी कारीगर व्यस्त हैं। कृपया कुछ देर बाद प्रयास करें।",
        )

    phone = next_worker.user.phone if next_worker.user else "0000"
    service = booking.service_request.service
    service_name = service.name if service else "Service"
    return VoiceBookingResponse(
        booking_id=new_booking.id,
        worker_name=next_worker.user.name if next_worker.user else "Worker",
        worker_phone_last4=phone[-4:] if phone else "****",
        service_name=service_name,
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
    """Status polling endpoint — frontend polls this after SMS dispatch. Auto-checks timeouts."""
    process_voice_booking_timeouts(db)

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


@voice_booking_router.post(
    "/voice-booking/check-timeouts",
    summary="Run timeout checks on pending voice bookings and auto-reassign expired offers",
)
def trigger_timeout_checks(
    db: Session = Depends(get_db),
):
    results = process_voice_booking_timeouts(db)
    return {"status": "ok", "processed_count": len(results), "results": results}
