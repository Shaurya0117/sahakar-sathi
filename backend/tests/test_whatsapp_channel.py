"""
Test suite for WhatsApp Service Booking Channel.
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


def test_whatsapp_unauthorized_phone_number(client: TestClient, db: Session):
    """Unknown phone number must be politely rejected without creating a request."""
    response = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": "+919999988888", "message": "Hi"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "UNAUTHORIZED"
    assert "We could not find a registered customer account" in data["reply"]


def test_whatsapp_full_booking_flow(client: TestClient, db: Session):
    """Complete multi-turn conversation over WhatsApp creating a valid ServiceRequest."""
    customer = ensure_test_customer(db)
    phone = customer.phone

    # Step 1: Start conversation
    res1 = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": phone, "message": "Hi"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["state"] == "SELECT_SERVICE"
    assert "Please reply with the number of your required service" in data1["reply"]

    # Step 2: Select service #2 (Electrical Repairs)
    res2 = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": phone, "message": "2"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["state"] == "DESCRIPTION"
    assert "Please briefly describe the problem" in data2["reply"]

    # Step 3: Provide description
    res3 = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": phone, "message": "Kitchen light switch panel spark issue"},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["state"] == "LOCATION"

    # Step 4: Provide location text
    res4 = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": phone, "message": "Sector 62, Noida"},
    )
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["state"] == "DATE"

    # Step 5: Provide date
    res5 = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": phone, "message": "Tomorrow"},
    )
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["state"] == "TIME"

    # Step 6: Provide time
    res6 = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": phone, "message": "2 PM"},
    )
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["state"] == "CONFIRMATION"
    assert "Please confirm your service request details" in data6["reply"]

    # Step 7: Confirm request
    res7 = client.post(
        "/api/channels/whatsapp/test-message",
        json={"phone": phone, "message": "1"},
    )
    assert res7.status_code == 200
    data7 = res7.json()
    assert data7["state"] == "REQUEST_CREATED"
    assert "Your service request has been submitted successfully" in data7["reply"]

    # Verify ServiceRequest exists in DB
    created_req = (
        db.query(ServiceRequest)
        .filter_by(customer_id=customer.id)
        .order_by(ServiceRequest.id.desc())
        .first()
    )
    assert created_req is not None
    assert created_req.status == RequestStatus.PENDING
    assert "Kitchen light switch panel spark issue" in created_req.description
    assert created_req.location == "Sector 62, Noida"


def test_whatsapp_location_payload_with_coordinates(client: TestClient, db: Session):
    """WhatsApp location drop should store latitude and longitude on ServiceRequest."""
    customer = ensure_test_customer(db)
    phone = customer.phone

    client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "reset"})
    client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "1"})
    client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "Pipe leak repair"})

    # Send location payload with coordinates
    res_loc = client.post(
        "/api/channels/whatsapp/test-message",
        json={
            "phone": phone,
            "message": "Near Block B Market",
            "latitude": 28.6272,
            "longitude": 77.3725,
        },
    )
    assert res_loc.json()["state"] == "DATE"

    client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "Tomorrow"})
    client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "10 AM"})
    res_confirm = client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "confirm"})

    assert res_confirm.json()["state"] == "REQUEST_CREATED"

    created_req = (
        db.query(ServiceRequest)
        .filter_by(customer_id=customer.id)
        .order_by(ServiceRequest.id.desc())
        .first()
    )
    assert created_req.latitude == 28.6272
    assert created_req.longitude == 77.3725


def test_whatsapp_cancellation(client: TestClient, db: Session):
    """Sending 'cancel' at any stage resets session state."""
    customer = ensure_test_customer(db)
    phone = customer.phone

    client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "Hi"})
    res_cancel = client.post("/api/channels/whatsapp/test-message", json={"phone": phone, "message": "cancel"})
    assert res_cancel.json()["state"] == "CANCELLED"
