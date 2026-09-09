"""
Test suite for Voice / IVR Service Booking Channel.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.services.auth import hash_password


def ensure_test_customer(db: Session) -> User:
    """Helper to ensure primary coop, service, and customer exist in in-memory test DB."""
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


def test_voice_ivr_unauthorized_caller(client: TestClient, db: Session):
    """Unknown caller phone number is rejected."""
    res = client.post(
        "/api/channels/voice/test-input",
        json={"phone": "+910000011111", "digits": "1"},
    )
    assert res.status_code == 200
    assert res.json()["state"] == "UNAUTHORIZED"


def test_voice_ivr_full_flow(client: TestClient, db: Session):
    """Complete IVR keypress flow resulting in a ServiceRequest."""
    customer = ensure_test_customer(db)
    phone = customer.phone

    # Start call
    res1 = client.post("/api/channels/voice/test-input", json={"phone": phone, "digits": "1"})
    assert res1.json()["state"] == "SELECT_SERVICE"

    # Select service 1 (Plumbing)
    res2 = client.post("/api/channels/voice/test-input", json={"phone": phone, "digits": "1"})
    assert res2.json()["state"] == "DESCRIPTION"

    # Provide task description
    res3 = client.post("/api/channels/voice/test-input", json={"phone": phone, "speech_text": "Water tap leakage in kitchen"})
    assert res3.json()["state"] == "LOCATION"

    # Provide location
    res4 = client.post("/api/channels/voice/test-input", json={"phone": phone, "speech_text": "Indirapuram Ghaziabad"})
    assert res4.json()["state"] == "DATE"

    # Provide date
    res5 = client.post("/api/channels/voice/test-input", json={"phone": phone, "speech_text": "Tomorrow"})
    assert res5.json()["state"] == "TIME"

    # Provide time
    res6 = client.post("/api/channels/voice/test-input", json={"phone": phone, "speech_text": "10 AM"})
    assert res6.json()["state"] == "CONFIRMATION"

    # Confirm (press 1)
    res7 = client.post("/api/channels/voice/test-input", json={"phone": phone, "digits": "1"})
    assert res7.json()["state"] == "REQUEST_CREATED"

    # Check request created
    created_req = (
        db.query(ServiceRequest)
        .filter_by(customer_id=customer.id)
        .order_by(ServiceRequest.id.desc())
        .first()
    )
    assert created_req is not None
    assert created_req.status == RequestStatus.PENDING
    assert "Water tap leakage" in created_req.description
