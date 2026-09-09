"""
Test suite for Channel Security & Provider Isolation.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.channels.providers.mock import MockVoiceProvider, MockWhatsAppProvider
from app.channels.providers.twilio import TwilioVoiceProvider, TwilioWhatsAppProvider
from app.models.user import User, UserRole
from app.services.auth import hash_password


def test_channel_worker_phone_rejection(client: TestClient, db: Session):
    """Worker phone number attempting booking without CUSTOMER role must be rejected."""
    worker_user = User(
        name="Rahul Kumar",
        email="rahul.worker.test@coopserve.demo",
        phone="+919876543210",
        password_hash=hash_password("Worker@1234"),
        role=UserRole.WORKER,
        is_active=True,
    )
    db.add(worker_user)
    db.commit()

    res = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": "+919876543210", "message": "Hi"},
    )
    assert res.status_code == 200
    assert res.json()["state"] == "UNAUTHORIZED"


def test_provider_factory_mock_mode():
    """Verify mock provider mode returns mock implementations."""
    p_wa = MockWhatsAppProvider()
    res_wa = p_wa.send_message("+919876500000", "Hello Test")
    assert res_wa["provider"] == "mock"

    p_voice = MockVoiceProvider()
    res_voice = p_voice.generate_ivr_response("Welcome")
    assert res_voice["provider"] == "mock"


def test_twilio_fallback_when_credentials_missing():
    """Twilio provider safely falls back when credentials are not configured."""
    p_wa = TwilioWhatsAppProvider()
    res_wa = p_wa.send_message("+919876500000", "Test")
    assert res_wa["status"] == "mock_fallback"
