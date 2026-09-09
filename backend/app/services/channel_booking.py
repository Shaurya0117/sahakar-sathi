"""
Channel Booking Service — Unified entry point for multi-channel bookings.
"""
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.channels.providers import get_voice_provider, get_whatsapp_provider
from app.services.conversation_state import process_channel_message


def handle_whatsapp_message(
    db: Session,
    raw_phone: str,
    message_text: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    send_response: bool = True,
) -> Dict[str, Any]:
    """
    Unified entry point for WhatsApp channel messages.
    Processes message state and optionally dispatches outbound WhatsApp message via provider.
    """
    reply_text, current_state = process_channel_message(
        db=db,
        channel="whatsapp",
        raw_phone=raw_phone,
        message_text=message_text,
        latitude=latitude,
        longitude=longitude,
    )

    outbound_status = None
    if send_response:
        provider = get_whatsapp_provider()
        outbound_status = provider.send_message(to_phone=raw_phone, message=reply_text)

    return {
        "reply": reply_text,
        "state": current_state,
        "phone": raw_phone,
        "provider_status": outbound_status,
    }


def handle_voice_input(
    db: Session,
    raw_phone: str,
    digits: Optional[str] = None,
    speech_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified entry point for Voice/IVR channel inputs.
    Processes digits/speech state and returns structured IVR response.
    """
    user_input = digits or speech_text or ""
    reply_text, current_state = process_channel_message(
        db=db,
        channel="voice",
        raw_phone=raw_phone,
        message_text=user_input,
    )

    voice_provider = get_voice_provider()
    ivr_payload = voice_provider.generate_ivr_response(
        say_text=reply_text,
        gather_action_url="/api/channels/voice/incoming",
        gather_num_digits=1,
    )

    return {
        "reply": reply_text,
        "state": current_state,
        "phone": raw_phone,
        "ivr_response": ivr_payload,
    }
