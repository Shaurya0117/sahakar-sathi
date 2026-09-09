"""
Mock Providers for WhatsApp and Voice channels (100% offline development & hackathon demo).
"""
import logging
from typing import Any, Dict

from app.channels.providers.base import BaseVoiceProvider, BaseWhatsAppProvider

logger = logging.getLogger(__name__)


class MockWhatsAppProvider(BaseWhatsAppProvider):
    """Mock WhatsApp provider that logs outbound messages for testing."""

    def send_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        logger.info(f"[MockWhatsApp] Outbound to {to_phone}:\n{message}")
        return {
            "status": "delivered",
            "provider": "mock",
            "to": to_phone,
            "body": message,
        }


class MockVoiceProvider(BaseVoiceProvider):
    """Mock Voice provider returning structured dict for testing."""

    def generate_ivr_response(
        self,
        say_text: str,
        gather_action_url: str = "/api/channels/voice/incoming",
        gather_num_digits: int = 1,
        finish_on_key: str = "#",
    ) -> Dict[str, Any]:
        logger.info(f"[MockVoice] IVR Say: {say_text}")
        return {
            "provider": "mock",
            "say": say_text,
            "gather": {
                "action": gather_action_url,
                "numDigits": gather_num_digits,
                "finishOnKey": finish_on_key,
            },
        }
