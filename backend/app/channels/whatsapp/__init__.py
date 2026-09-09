"""WhatsApp channel package."""
from app.channels.whatsapp.webhook import router as whatsapp_router

__all__ = ["whatsapp_router"]
