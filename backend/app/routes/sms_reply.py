"""
SMS Reply Webhook — Sahakar Sathi.

Handles worker SMS replies (1=Accept, 2=Decline) and simulation endpoint for demo.

Real production flow (Android SMS Gateway):
  Worker replies "1" → Android phone receives SMS → Gateway webhooks POST /api/sms/reply

Demo flow (Textbelt doesn't support incoming):
  Admin/demo uses POST /api/sms/simulate-reply to simulate worker reply
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database.session import get_db
from app.models.booking import Booking, BookingStatus
from app.models.user import User
from app.services.sms_service import (
    build_hindi_confirmation_sms,
    build_hindi_fallback_sms,
    send_sms,
)

logger = logging.getLogger(__name__)

sms_reply_router = APIRouter(tags=["SMS Reply"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SmsReplyWebhook(BaseModel):
    """
    Incoming SMS reply from Android SMS Gateway webhook.
    The gateway POSTs this when a worker replies by SMS.
    """
    from_phone: str   # E.164: +919XXXXXXXXX
    message: str      # "1" or "2" (accept/decline)
    timestamp: str = ""


class SimulateReplyRequest(BaseModel):
    """Demo endpoint — simulate a worker SMS reply without a real phone."""
    booking_id: int
    reply: str        # "1" (accept) or "2" (decline)


class SmsReplyResponse(BaseModel):
    success: bool
    booking_id: int
    new_status: str
    message: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _process_reply(booking: Booking, reply: str, db: Session) -> SmsReplyResponse:
    """
    Core logic: parse reply "1"/"2" and update booking status accordingly.
    Sends Hindi confirmation SMS back to worker.
    """
    reply = reply.strip()

    if reply == "1":
        # Worker ACCEPTED
        booking.status = BookingStatus.ACCEPTED
        db.commit()

        # Send Hindi confirmation to worker
        worker = booking.worker
        if worker and worker.user and worker.user.phone:
            msg = build_hindi_confirmation_sms(accepted=True, booking_id=booking.id)
            send_sms(worker.user.phone, msg)

        logger.info("Booking #%s ACCEPTED by worker #%s", booking.id, booking.worker_id)
        return SmsReplyResponse(
            success=True,
            booking_id=booking.id,
            new_status="ACCEPTED",
            message=f"🎉 Worker accepted booking #{booking.id}! Confirmed.",
        )

    elif reply == "2":
        # Worker DECLINED
        booking.status = BookingStatus.REJECTED
        db.commit()

        # Notify worker
        worker = booking.worker
        if worker and worker.user and worker.user.phone:
            msg = build_hindi_fallback_sms(booking.id)
            send_sms(worker.user.phone, msg)

        logger.info("Booking #%s DECLINED by worker #%s — needs fallback", booking.id, booking.worker_id)
        return SmsReplyResponse(
            success=True,
            booking_id=booking.id,
            new_status="REJECTED",
            message=f"Worker declined booking #{booking.id}. Use /api/voice-booking/fallback to reassign.",
        )

    else:
        logger.warning("Unknown SMS reply '%s' for booking #%s", reply, booking.id)
        return SmsReplyResponse(
            success=False,
            booking_id=booking.id,
            new_status=booking.status.value,
            message=f"Unknown reply '{reply}'. Expected '1' (accept) or '2' (decline).",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@sms_reply_router.post(
    "/sms/reply",
    response_model=SmsReplyResponse,
    summary="Incoming SMS reply webhook from Android SMS Gateway",
)
def sms_reply_webhook(
    payload: SmsReplyWebhook,
    db: Session = Depends(get_db),
):
    """
    Android SMS Gateway POSTs here when a worker replies by SMS.
    Matches the worker's phone number to find their active booking.

    Note: This endpoint intentionally has no auth — the Gateway can't carry JWT.
    In production, validate with a webhook secret header.
    """
    phone = payload.from_phone.strip()

    # Find the most recent ASSIGNED booking for this worker's phone
    # We join Worker → User and match on phone
    from app.models.worker import Worker
    from app.models.user import User as UserModel

    worker = (
        db.query(Worker)
        .join(UserModel, Worker.user_id == UserModel.id)
        .filter(UserModel.phone == phone)
        .first()
    )
    if not worker:
        # Try without + prefix
        normalized = phone.lstrip("+")
        worker = (
            db.query(Worker)
            .join(UserModel, Worker.user_id == UserModel.id)
            .filter(UserModel.phone.contains(normalized[-10:]))
            .first()
        )

    if not worker:
        logger.warning("SMS reply from unknown phone %s", phone[-4:])
        raise HTTPException(status_code=404, detail=f"No worker found with phone ending {phone[-4:]}")

    # Find the latest ASSIGNED booking for this worker
    booking = (
        db.query(Booking)
        .filter(
            Booking.worker_id == worker.id,
            Booking.status == BookingStatus.ASSIGNED,
        )
        .order_by(Booking.created_at.desc())
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="No active (ASSIGNED) booking found for this worker")

    return _process_reply(booking, payload.message, db)


@sms_reply_router.post(
    "/sms/simulate-reply",
    response_model=SmsReplyResponse,
    summary="Demo: Simulate a worker SMS reply (for demo without a real phone)",
)
def simulate_sms_reply(
    payload: SimulateReplyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Demo endpoint: simulate a worker replying '1' (accept) or '2' (decline).
    Accessible by any logged-in user for demo purposes.
    In production, restrict to admin or the worker themselves.
    """
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking #{payload.booking_id} not found")

    if booking.status != BookingStatus.ASSIGNED:
        raise HTTPException(
            status_code=400,
            detail=f"Booking is in '{booking.status.value}' state — can only simulate reply for ASSIGNED bookings",
        )

    return _process_reply(booking, payload.reply, db)
