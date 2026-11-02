"""
WhatsApp API Webhook & Test Endpoints.

POST /api/channels/whatsapp/webhook — Provider Webhook (Telnyx / Twilio / External)
POST /api/channels/whatsapp/test-message — Development / Hackathon Demo Mock Endpoint
"""
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.channels.whatsapp.parser import parse_whatsapp_payload
from app.config import settings
from app.database import get_db
from app.services.channel_booking import handle_whatsapp_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels/whatsapp", tags=["WhatsApp Channel"])

# In-memory idempotency cache for duplicate webhook event IDs
PROCESSED_EVENT_IDS: Set[str] = set()


def is_duplicate_event(event_id: Optional[str]) -> bool:
    """Return True if event_id has already been processed."""
    if not event_id:
        return False
    if event_id in PROCESSED_EVENT_IDS:
        return True
    PROCESSED_EVENT_IDS.add(event_id)
    if len(PROCESSED_EVENT_IDS) > 5000:
        PROCESSED_EVENT_IDS.clear()
    return False


def verify_telnyx_signature(raw_body: bytes, headers: Dict[str, str]) -> bool:
    """
    Verify incoming Telnyx webhook signature against TELNYX_WEBHOOK_SECRET.
    If TELNYX_WEBHOOK_SECRET is not configured, allows requests for local testing.
    """
    secret = (settings.TELNYX_WEBHOOK_SECRET or "").strip()
    if not secret:
        return True

    sig_header = (
        headers.get("telnyx-signature-ed25519")
        or headers.get("x-telnyx-signature")
        or headers.get("telnyx-signature")
        or ""
    )
    timestamp_header = (
        headers.get("telnyx-timestamp")
        or headers.get("x-telnyx-timestamp")
        or ""
    )

    if not sig_header:
        logger.warning("[TelnyxWebhook] Missing signature header.")
        return False

    # Check HMAC-SHA256 timestamp signature or direct token match
    signed_payload = f"{timestamp_header}|{raw_body.decode('utf-8', errors='ignore')}".encode("utf-8")
    expected_hmac = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

    if hmac.compare_digest(sig_header.lower(), expected_hmac.lower()) or hmac.compare_digest(sig_header, secret):
        return True

    logger.warning("[TelnyxWebhook] Webhook signature verification failed.")
    return False


class WhatsAppTestMessageRequest(BaseModel):
    phone: str = Field(..., description="Customer phone number (e.g. +919876500000)")
    message: Optional[str] = Field(None, description="Inbound text message")
    latitude: Optional[float] = Field(None, description="Optional GPS latitude (-90.0 to 90.0)")
    longitude: Optional[float] = Field(None, description="Optional GPS longitude (-180.0 to 180.0)")


@router.post("/webhook", summary="WhatsApp Provider Webhook")
async def whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public webhook receiver for incoming WhatsApp messages from Telnyx, Twilio, or external providers.
    Supports application/json and application/x-www-form-urlencoded payloads.
    Verifies signatures when configured, supports idempotency, and dispatches outbound replies.
    """
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    is_dev = settings.APP_ENV.lower() in ("development", "dev", "test", "testing")
    telnyx_secret = (settings.TELNYX_WEBHOOK_SECRET or "").strip()
    twilio_secret = (settings.TWILIO_WEBHOOK_SECRET or "").strip()

    # Provider security verification
    if settings.WHATSAPP_PROVIDER.lower() == "telnyx":
        if telnyx_secret:
            header_dict = {k.lower(): v for k, v in request.headers.items()}
            if not verify_telnyx_signature(raw_body, header_dict):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Telnyx webhook signature.",
                )
        elif not is_dev:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telnyx webhook secret not configured in production.",
            )
    elif settings.WHATSAPP_PROVIDER.lower() == "twilio":
        if twilio_secret:
            sig_header = request.headers.get("x-twilio-signature") or request.headers.get("x-webhook-secret") or ""
            expected_hmac = hmac.new(twilio_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
            if not (hmac.compare_digest(sig_header, twilio_secret) or hmac.compare_digest(sig_header.lower(), expected_hmac.lower())):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Twilio webhook signature.",
                )
        elif not is_dev:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Twilio webhook secret not configured in production.",
            )
    elif not is_dev:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="WhatsApp provider webhook requires authentication in production.",
        )

    if "x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload = dict(form_data)
    else:
        try:
            import json
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            payload = {}

    phone, message_text, lat, lng, event_id = parse_whatsapp_payload(payload)

    # Check for duplicate webhook retries
    if event_id and is_duplicate_event(event_id):
        logger.info(f"[WhatsAppWebhook] Ignoring duplicate event_id: {event_id}")
        return {"status": "duplicate_ignored", "event_id": event_id}

    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing sender phone number in payload.",
        )

    result = handle_whatsapp_message(
        db=db,
        raw_phone=phone,
        message_text=message_text,
        latitude=lat,
        longitude=lng,
        send_response=True,
    )

    return result


@router.post("/test-message", summary="Test WhatsApp Conversation (Mock Mode)")
def whatsapp_test_message(
    payload: WhatsAppTestMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Development & Hackathon Demo endpoint to simulate WhatsApp messages.
    Uses the exact same conversation service as the real provider webhook.
    Disabled outside development/test environments.
    """
    is_dev = settings.APP_ENV.lower() in ("development", "dev", "test", "testing")
    if not is_dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found",
        )

    result = handle_whatsapp_message(
        db=db,
        raw_phone=payload.phone,
        message_text=payload.message,
        latitude=payload.latitude,
        longitude=payload.longitude,
        send_response=False,
    )
    return result
