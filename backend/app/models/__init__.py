"""Models package — SQLAlchemy ORM models."""
# Import each model here so that Base.metadata registers the table.
# The side-effect import in app.main triggers create_all() for all listed models.
from app.models.booking import Booking, BookingStatus  # noqa: F401
from app.models.conversation_session import ConversationSession  # noqa: F401
from app.models.cooperative import Cooperative  # noqa: F401
from app.models.service import Service  # noqa: F401
from app.models.service_request import RequestStatus, ServiceRequest  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "Worker",
    "VerificationStatus",
    "AvailabilityStatus",
    "Cooperative",
    "Service",
    "ServiceRequest",
    "RequestStatus",
    "Booking",
    "BookingStatus",
    "ConversationSession",
]
