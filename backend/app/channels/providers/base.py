"""
Base Provider Interfaces for WhatsApp and Voice channels.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseWhatsAppProvider(ABC):
    """Abstract interface for WhatsApp messaging providers."""

    @abstractmethod
    def send_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send a WhatsApp message to a recipient."""
        pass


class BaseVoiceProvider(ABC):
    """Abstract interface for Voice/IVR providers."""

    @abstractmethod
    def generate_ivr_response(
        self,
        say_text: str,
        gather_action_url: str = "/api/channels/voice/incoming",
        gather_num_digits: int = 1,
        finish_on_key: str = "#",
    ) -> Any:
        """Generate IVR response (TwiML XML or Mock response)."""
        pass
