"""
Voice / IVR Webhook & Test Endpoints.

POST /api/channels/voice/incoming — Voice Provider Webhook (Twilio / External IVR)
POST /api/channels/voice/test-input — Development / Hackathon Demo Voice Simulation Endpoint
"""
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.channel_booking import handle_voice_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels/voice", tags=["Voice Channel"])


class VoiceTestInputRequest(BaseModel):
    phone: str = Field(..., description="Customer phone number (e.g. +919876500000)")
    digits: Optional[str] = Field(None, description="Keypad DTMF digits pressed (e.g. '1')")
    speech_text: Optional[str] = Field(None, description="Spoken voice transcript if available")


@router.post("/incoming", summary="Voice / IVR Provider Webhook")
async def voice_incoming_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public webhook receiver for incoming phone calls and DTMF digit inputs from Twilio Voice.
    Returns TwiML XML response for Twilio or JSON structure for mock providers.
    Verifies signature if configured; rejects outside dev if secret is not set.
    """
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")

    # Security verification
    is_dev = settings.APP_ENV.lower() in ("development", "dev", "test", "testing")
    twilio_secret = (settings.TWILIO_WEBHOOK_SECRET or "").strip()

    if twilio_secret:
        sig_header = (
            request.headers.get("x-twilio-signature")
            or request.headers.get("x-webhook-secret")
            or ""
        )
        if not sig_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Twilio webhook signature.",
            )
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

    if "x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload = dict(form_data)
    else:
        try:
            import json
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception:
            payload = {}

    phone = payload.get("From") or payload.get("phone") or payload.get("Caller") or ""
    digits = payload.get("Digits") or payload.get("digits") or None
    speech_text = payload.get("SpeechResult") or payload.get("speech_text") or None

    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing caller phone number in payload.",
        )

    result = handle_voice_input(
        db=db,
        raw_phone=phone,
        digits=digits,
        speech_text=speech_text,
    )

    # If provider status returns FastAPI Response (TwiML XML), return it directly
    ivr_res = result.get("ivr_response")
    if hasattr(ivr_res, "body"):
        return ivr_res

    return result


@router.post("/test-input", summary="Test Voice IVR Conversation (Mock Mode)")
def voice_test_input(
    payload: VoiceTestInputRequest,
    db: Session = Depends(get_db),
):
    """
    Development & Hackathon Demo endpoint to simulate Voice IVR interactions.
    Uses the exact same conversation service as the real provider webhook.
    Disabled outside development/test environments.
    """
    is_dev = settings.APP_ENV.lower() in ("development", "dev", "test", "testing")
    if not is_dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not found",
        )

    result = handle_voice_input(
        db=db,
        raw_phone=payload.phone,
        digits=payload.digits,
        speech_text=payload.speech_text,
    )
    return result
