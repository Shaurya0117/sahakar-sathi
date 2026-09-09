"""
Provider Factory to return active WhatsApp or Voice provider based on configuration.
"""
from app.channels.providers.base import BaseVoiceProvider, BaseWhatsAppProvider
from app.channels.providers.mock import MockVoiceProvider, MockWhatsAppProvider
from app.channels.providers.telnyx import TelnyxWhatsAppProvider
from app.channels.providers.twilio import TwilioVoiceProvider, TwilioWhatsAppProvider
from app.config import settings


def get_whatsapp_provider() -> BaseWhatsAppProvider:
    provider = settings.WHATSAPP_PROVIDER.lower().strip()
    if provider == "telnyx":
        return TelnyxWhatsAppProvider()
    elif provider == "twilio":
        return TwilioWhatsAppProvider()
    elif provider == "mock":
        return MockWhatsAppProvider()
    else:
        raise ValueError(
            f"Invalid WHATSAPP_PROVIDER configuration '{settings.WHATSAPP_PROVIDER}'. "
            f"Allowed values are 'mock', 'twilio', or 'telnyx'."
        )


def get_voice_provider() -> BaseVoiceProvider:
    if settings.VOICE_PROVIDER.lower() == "twilio":
        return TwilioVoiceProvider()
    return MockVoiceProvider()
