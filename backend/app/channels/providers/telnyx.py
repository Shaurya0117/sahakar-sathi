"""
Telnyx WhatsApp Provider Implementation.

Uses Telnyx Messages REST API (v2) with urllib.request for zero third-party dependency.
"""
import json
import logging
import urllib.request
from typing import Any, Dict

from app.channels.providers.base import BaseWhatsAppProvider
from app.config import settings

logger = logging.getLogger(__name__)


class TelnyxWhatsAppProvider(BaseWhatsAppProvider):
    """
    Telnyx WhatsApp provider using Telnyx Messages REST API v2.
    https://developers.telnyx.com/docs/api/v2/messaging/Messages#createMessage
    """

    def send_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        if not settings.TELNYX_API_KEY:
            logger.info("[TelnyxWhatsApp] Missing TELNYX_API_KEY, operating in mock fallback mode.")
            return {
                "status": "mock_fallback",
                "provider": "telnyx",
                "to": to_phone,
                "body": message,
            }

        # Normalize target phone number (Telnyx expects standard E.164 format e.g. +919876500000)
        clean_target = to_phone.replace("whatsapp:", "").strip()
        if not clean_target.startswith("+") and len(clean_target) == 10:
            clean_target = f"+91{clean_target}"

        sender = settings.TELNYX_WHATSAPP_NUMBER or ""
        clean_sender = sender.replace("whatsapp:", "").strip()

        url = "https://api.telnyx.com/v2/messages"
        headers = {
            "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "CoopServe-WhatsApp-Service/1.0",
        }

        payload: Dict[str, Any] = {
            "from": clean_sender,
            "to": clean_target,
            "text": message,
            "type": "whatsapp",
        }

        if settings.TELNYX_MESSAGING_PROFILE_ID:
            payload["messaging_profile_id"] = settings.TELNYX_MESSAGING_PROFILE_ID

        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_body = response.read().decode("utf-8")
                result = json.loads(resp_body)
                logger.info(f"[TelnyxWhatsApp] Successfully dispatched message to {clean_target}")
                return result
        except Exception as e:
            logger.error(f"[TelnyxWhatsApp] Failed to dispatch Telnyx message to {clean_target}: {e}")
            return {"status": "error", "detail": str(e), "body": message, "provider": "telnyx"}
