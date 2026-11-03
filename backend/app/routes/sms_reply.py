"""
SMS Reply Webhook — Sahakar Sathi.

Handles worker SMS replies (1=Accept, 2=Decline) and simulation endpoint for demo.

Production flow (Android SMS Gateway):
  Worker replies "1" → Android phone receives SMS → Gateway webhooks POST /api/sms/reply
  Protected by X-Webhook-Secret authentication and rate limiting.

Demo flow:
  Admin/demo uses POST /api/sms/simulate-reply to simulate worker reply (disabled in production).
"""
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.rate_limiter import check_rate_limit, get_client_ip
from app.config import settings
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
    request: Request,
    payload: SmsReplyWebhook,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    secret: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Android SMS Gateway POSTs here when a worker replies by SMS.
    Protected by webhook secret check (header X-Webhook-Secret or ?secret= query parameter),
    timestamp age validation, and two-tier rate limiting (10/min per phone, 120/min per gateway IP).
    """
    # 1. Two-tier Rate limiting
    # Loose IP backstop (120 req/min) so one Android Gateway IP can service multiple workers
    ip = get_client_ip(request)
    check_rate_limit(f"ip:{ip}", "sms_reply_ip", max_requests=120, window_seconds=60)

    # Primary limit: per from_phone (10 req/min, fallback to IP if missing)
    phone_key = (payload.from_phone or "").strip() or ip
    check_rate_limit(f"phone:{phone_key}", "sms_reply_phone", max_requests=10, window_seconds=60)

    # 2. Authenticate webhook secret using timing-safe comparison
    # Support both custom header (X-Webhook-Secret) and query param (?secret=)
    configured_secret = (getattr(settings, "SMS_WEBHOOK_SECRET", "") or "").strip()
    if settings.APP_ENV == "production" and not configured_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SMS webhook rejected: secret not configured in production",
        )

    header_secret = (x_webhook_secret or "").strip()
    query_secret = (secret or "").strip()

    header_valid = bool(configured_secret and header_secret and hmac.compare_digest(header_secret, configured_secret))
    query_valid = bool(configured_secret and query_secret and hmac.compare_digest(query_secret, configured_secret))

    if not (header_valid or query_valid):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: invalid or missing webhook secret (provide X-Webhook-Secret header or ?secret= query parameter)",
        )

    # 3. Ignore replies older than 24 hours
    if payload.timestamp:
        try:
            ts_str = payload.timestamp.strip()
            if ts_str.isdigit() or ts_str.replace(".", "", 1).isdigit():
                ts_num = float(ts_str)
                if ts_num > 1e11:  # Epoch milliseconds
                    ts_num /= 1000.0
                msg_time = datetime.fromtimestamp(ts_num, tz=timezone.utc)
            else:
                msg_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

            now = datetime.now(timezone.utc)
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=timezone.utc)

            if (now - msg_time).total_seconds() > 86400:  # 24 hours
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ignored: reply older than 24 hours",
                )
        except (ValueError, TypeError) as e:
            logger.warning("Could not parse SMS timestamp '%s': %s", payload.timestamp, e)

    # 4. Lookup worker associated with this phone number
    phone = payload.from_phone.strip()
    from app.models.worker import Worker
    from app.models.user import User as UserModel

    worker = (
        db.query(Worker)
        .join(UserModel, Worker.user_id == UserModel.id)
        .filter(UserModel.phone == phone)
        .first()
    )
    if not worker:
        normalized = phone.lstrip("+")
        worker = (
            db.query(Worker)
            .join(UserModel, Worker.user_id == UserModel.id)
            .filter(UserModel.phone.contains(normalized[-10:]))
            .first()
        )

    if not worker:
        logger.warning("SMS reply from unknown phone %s", phone[-4:])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ignored: no worker found with phone ending {phone[-4:]}",
        )

    # 5. Lookup the worker's active (ASSIGNED) booking
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
        logger.info("Ignored: worker %s has no active (ASSIGNED) booking", worker.id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ignored: no pending booking for this phone number",
        )

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
    Accessible by any logged-in user for demo purposes outside of production.
    """
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Simulate reply endpoint is disabled in production",
        )

    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking #{payload.booking_id} not found")

    if booking.status != BookingStatus.ASSIGNED:
        raise HTTPException(
            status_code=400,
            detail=f"Booking is in '{booking.status.value}' state — can only simulate reply for ASSIGNED bookings",
        )

    return _process_reply(booking, payload.reply, db)
