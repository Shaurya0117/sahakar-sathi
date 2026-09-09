"""
Voice / IVR Webhook & Test Endpoints.

POST /api/channels/voice/incoming — Voice Provider Webhook (Twilio / External IVR)
POST /api/channels/voice/test-input — Development / Hackathon Demo Voice Simulation Endpoint
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

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
    """
    content_type = request.headers.get("content-type", "")

    if "x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        payload = dict(form_data)
    else:
        try:
            payload = await request.json()
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
    """
    result = handle_voice_input(
        db=db,
        raw_phone=payload.phone,
        digits=payload.digits,
        speech_text=payload.speech_text,
    )
    return result
