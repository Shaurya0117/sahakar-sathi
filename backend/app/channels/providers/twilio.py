"""
Twilio Provider implementation for real WhatsApp & Voice integrations.
Uses urllib.request / httpx for zero unnecessary third-party dependencies.
"""
import base64
import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict

from fastapi.responses import Response

from app.channels.providers.base import BaseVoiceProvider, BaseWhatsAppProvider
from app.config import settings

logger = logging.getLogger(__name__)


class TwilioWhatsAppProvider(BaseWhatsAppProvider):
    """Twilio WhatsApp provider using Twilio Messages REST API."""

    def send_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.info("[TwilioWhatsApp] Missing credentials, operating in mock fallback mode.")
            return {
                "status": "mock_fallback",
                "provider": "twilio",
                "to": to_phone,
                "body": message,
            }

        sender = settings.TWILIO_WHATSAPP_NUMBER or "whatsapp:+14155238886"
        target = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"

        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        
        auth_bytes = f"{settings.TWILIO_ACCOUNT_SID}:{settings.TWILIO_AUTH_TOKEN}".encode("utf-8")
        auth_header = f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"

        data = urllib.parse.urlencode({
            "From": sender,
            "To": target,
            "Body": message,
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", auth_header)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except Exception as e:
            logger.error(f"[TwilioWhatsApp] Failed to send message: {e}")
            return {"status": "error", "detail": str(e), "body": message}


class TwilioVoiceProvider(BaseVoiceProvider):
    """Twilio Voice provider returning TwiML XML responses."""

    def generate_ivr_response(
        self,
        say_text: str,
        gather_action_url: str = "/api/channels/voice/incoming",
        gather_num_digits: int = 1,
        finish_on_key: str = "#",
    ) -> Response:
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather action="{gather_action_url}" numDigits="{gather_num_digits}" finishOnKey="{finish_on_key}">
        <Say voice="alice">{say_text}</Say>
    </Gather>
    <Say voice="alice">We did not receive any input. Goodbye.</Say>
</Response>"""
        return Response(content=xml_content, media_type="application/xml")
