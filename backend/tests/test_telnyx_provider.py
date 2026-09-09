"""
Test suite for Telnyx WhatsApp Integration, Webhook Parser, Idempotency, Signature Security, and Provider Factory.
"""
import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.channels.providers import get_whatsapp_provider
from app.channels.providers.mock import MockWhatsAppProvider
from app.channels.providers.telnyx import TelnyxWhatsAppProvider
from app.channels.providers.twilio import TwilioWhatsAppProvider
from app.channels.whatsapp.parser import parse_whatsapp_payload
from app.channels.whatsapp.webhook import is_duplicate_event, verify_telnyx_signature
from app.config import settings
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.services.auth import hash_password


def ensure_test_customer(db: Session) -> User:
    """Helper to ensure primary coop, service, and customer exist in test DB."""
    coop = db.query(Cooperative).first()
    if not coop:
        coop = Cooperative(name="Ghaziabad Community Coop", location="Ghaziabad")
        db.add(coop)
        db.commit()

    if db.query(Service).count() == 0:
        s1 = Service(name="Plumbing & Sanitation", category="Household", is_active=True)
        s2 = Service(name="Electrical Repairs & Maintenance", category="Household", is_active=True)
        db.add(s1)
        db.add(s2)
        db.commit()

    customer = db.query(User).filter_by(email="asha.customer@coopserve.demo").first()
    if not customer:
        customer = User(
            name="Asha Sharma",
            email="asha.customer@coopserve.demo",
            phone="+919876500000",
            password_hash=hash_password("Customer@1234"),
            role=UserRole.CUSTOMER,
            is_active=True,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    return customer


def test_telnyx_inbound_message_parsing():
    """Test parse_whatsapp_payload with Telnyx v2 JSON webhook structure."""
    telnyx_payload = {
        "data": {
            "event_type": "message.received",
            "id": "evt_123456789",
            "payload": {
                "id": "msg_987654321",
                "direction": "inbound",
                "from": {"phone_number": "+919876500000"},
                "text": "Need plumbing service",
                "type": "whatsapp",
            },
        }
    }
    phone, text, lat, lng, event_id = parse_whatsapp_payload(telnyx_payload)

    assert phone == "+919876500000"
    assert text == "Need plumbing service"
    assert lat is None
    assert lng is None
    assert event_id == "evt_123456789"


def test_telnyx_gps_location_message_parsing():
    """Test parse_whatsapp_payload with Telnyx location drop object."""
    telnyx_loc_payload = {
        "data": {
            "event_type": "message.received",
            "id": "evt_loc_001",
            "payload": {
                "id": "msg_loc_001",
                "from": {"phone_number": "+919876500000"},
                "type": "whatsapp",
                "location": {
                    "latitude": 28.6272,
                    "longitude": 77.3725,
                    "name": "Block B Market",
                    "address": "Sector 62, Noida",
                },
            },
        }
    }
    phone, text, lat, lng, event_id = parse_whatsapp_payload(telnyx_loc_payload)

    assert phone == "+919876500000"
    assert lat == 28.6272
    assert lng == 77.3725
    assert event_id == "evt_loc_001"
    assert "Sector 62, Noida" in (text or "")


def test_telnyx_outbound_message_payload_dispatch():
    """Test TelnyxWhatsAppProvider outbound REST API call format."""
    provider = TelnyxWhatsAppProvider()
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": {"id": "msg_outbound_001"}}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Temporarily set API key
        original_key = settings.TELNYX_API_KEY
        settings.TELNYX_API_KEY = "KEY0123456789"
        try:
            res = provider.send_message("+919876500000", "Hello Asha")
            assert res["data"]["id"] == "msg_outbound_001"

            # Verify request headers and URL
            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "https://api.telnyx.com/v2/messages"
            assert req.headers["Authorization"] == "Bearer KEY0123456789"
            payload = json.loads(req.data.decode("utf-8"))
            assert payload["to"] == "+919876500000"
            assert payload["text"] == "Hello Asha"
            assert payload["type"] == "whatsapp"
        finally:
            settings.TELNYX_API_KEY = original_key


def test_provider_factory_selection():
    """Test provider factory for mock, twilio, and telnyx modes."""
    orig = settings.WHATSAPP_PROVIDER

    try:
        settings.WHATSAPP_PROVIDER = "mock"
        assert isinstance(get_whatsapp_provider(), MockWhatsAppProvider)

        settings.WHATSAPP_PROVIDER = "twilio"
        assert isinstance(get_whatsapp_provider(), TwilioWhatsAppProvider)

        settings.WHATSAPP_PROVIDER = "telnyx"
        assert isinstance(get_whatsapp_provider(), TelnyxWhatsAppProvider)
    finally:
        settings.WHATSAPP_PROVIDER = orig


def test_telnyx_webhook_end_to_end_flow(client: TestClient, db: Session):
    """Full multi-turn booking flow simulating Telnyx inbound webhooks."""
    customer = ensure_test_customer(db)
    phone = customer.phone

    orig_provider = settings.WHATSAPP_PROVIDER
    settings.WHATSAPP_PROVIDER = "telnyx"

    try:
        def make_telnyx_req(text_msg: str, evt_id: str, lat: float = None, lng: float = None):
            payload_dict = {
                "data": {
                    "event_type": "message.received",
                    "id": evt_id,
                    "payload": {
                        "from": {"phone_number": phone},
                        "text": text_msg,
                    },
                }
            }
            if lat and lng:
                payload_dict["data"]["payload"]["location"] = {"latitude": lat, "longitude": lng}
            return client.post("/api/channels/whatsapp/webhook", json=payload_dict)

        # Reset session
        make_telnyx_req("reset", "evt_t00")

        # 1. Start conversation
        r1 = make_telnyx_req("Hi", "evt_t01")
        assert r1.status_code == 200
        assert r1.json()["state"] == "SELECT_SERVICE"

        # 2. Select service 1 (Plumbing)
        r2 = make_telnyx_req("1", "evt_t02")
        assert r2.json()["state"] == "DESCRIPTION"

        # 3. Description
        r3 = make_telnyx_req("Tap leaking in bathroom", "evt_t03")
        assert r3.json()["state"] == "LOCATION"

        # 4. Location text
        r4 = make_telnyx_req("Vasundhara, Ghaziabad", "evt_t04")
        assert r4.json()["state"] == "DATE"

        # 5. Date
        r5 = make_telnyx_req("Tomorrow", "evt_t05")
        assert r5.json()["state"] == "TIME"

        # 6. Time
        r6 = make_telnyx_req("11 AM", "evt_t06")
        assert r6.json()["state"] == "CONFIRMATION"

        # 7. Confirmation
        r7 = make_telnyx_req("1", "evt_t07")
        assert r7.json()["state"] == "REQUEST_CREATED"

        # Check DB ServiceRequest
        created = db.query(ServiceRequest).filter_by(customer_id=customer.id).order_by(ServiceRequest.id.desc()).first()
        assert created is not None
        assert created.status == RequestStatus.PENDING
        assert "Tap leaking" in created.description

    finally:
        settings.WHATSAPP_PROVIDER = orig_provider


def test_telnyx_webhook_unknown_phone_number(client: TestClient, db: Session):
    """Unknown phone number via Telnyx webhook is rejected."""
    telnyx_payload = {
        "data": {
            "event_type": "message.received",
            "id": "evt_unk_001",
            "payload": {
                "from": {"phone_number": "+919999911111"},
                "text": "Hi",
            },
        }
    }
    res = client.post("/api/channels/whatsapp/webhook", json=telnyx_payload)
    assert res.status_code == 200
    assert res.json()["state"] == "UNAUTHORIZED"


def test_telnyx_webhook_cancellation(client: TestClient, db: Session):
    """Sending 'cancel' via Telnyx payload resets state."""
    customer = ensure_test_customer(db)
    phone = customer.phone

    payload = {
        "data": {
            "event_type": "message.received",
            "id": "evt_cancel_001",
            "payload": {
                "from": {"phone_number": phone},
                "text": "cancel",
            },
        }
    }
    res = client.post("/api/channels/whatsapp/webhook", json=payload)
    assert res.status_code == 200
    assert res.json()["state"] == "CANCELLED"


def test_malformed_telnyx_payload(client: TestClient):
    """Malformed Telnyx payload missing phone should return HTTP 400."""
    res = client.post("/api/channels/whatsapp/webhook", json={"data": {"event_type": "message.received"}})
    assert res.status_code == 400
    assert "Missing sender phone number" in res.json()["detail"]


def test_duplicate_webhook_idempotency(client: TestClient, db: Session):
    """Duplicate event_id from Telnyx webhook should be ignored on retry."""
    customer = ensure_test_customer(db)
    phone = customer.phone

    payload = {
        "data": {
            "event_type": "message.received",
            "id": "evt_duplicate_test_100",
            "payload": {
                "from": {"phone_number": phone},
                "text": "Hi",
            },
        }
    }

    # First delivery
    res1 = client.post("/api/channels/whatsapp/webhook", json=payload)
    assert res1.status_code == 200
    assert res1.json()["state"] == "SELECT_SERVICE"

    # Second delivery (retry with same event_id)
    res2 = client.post("/api/channels/whatsapp/webhook", json=payload)
    assert res2.status_code == 200
    assert res2.json()["status"] == "duplicate_ignored"


def test_telnyx_signature_verification_security(client: TestClient):
    """Test signature verification when TELNYX_WEBHOOK_SECRET is configured."""
    orig_provider = settings.WHATSAPP_PROVIDER
    orig_secret = settings.TELNYX_WEBHOOK_SECRET

    try:
        settings.WHATSAPP_PROVIDER = "telnyx"
        settings.TELNYX_WEBHOOK_SECRET = "super-secret-webhook-key"

        # Missing signature headers -> 401 Unauthorized
        res_fail = client.post("/api/channels/whatsapp/webhook", json={"phone": "+919876500000"})
        assert res_fail.status_code == 401
        assert "Invalid Telnyx webhook signature" in res_fail.json()["detail"]

        # Secret matching header -> Passes verification
        res_pass = client.post(
            "/api/channels/whatsapp/webhook",
            headers={"telnyx-signature-ed25519": "super-secret-webhook-key"},
            json={
                "data": {
                    "event_type": "message.received",
                    "id": "evt_sig_pass",
                    "payload": {
                        "from": {"phone_number": "+919876500000"},
                        "text": "Hi",
                    },
                }
            },
        )
        assert res_pass.status_code == 200

    finally:
        settings.WHATSAPP_PROVIDER = orig_provider
        settings.TELNYX_WEBHOOK_SECRET = orig_secret
