"""
ServiceRequest tests — 20 test cases covering customer request flow, validation, and security.

Run:
    cd backend
    pytest tests/test_service_requests.py -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def register(email, password="Password1", role="CUSTOMER", name="Test User"):
    return client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": password,
        "role": role,
    })


def login(email, password="Password1"):
    return client.post("/api/auth/login", data={
        "username": email,
        "password": password,
    })


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def setup_base_data():
    from tests.conftest import TestingSessionLocal
    from app.services.auth import create_admin_if_absent
    from app.services.cooperative import ensure_demo_cooperative
    from app.services.service_catalog import ensure_seed_services

    db = TestingSessionLocal()
    admin = create_admin_if_absent(db, "Admin", "admin@test.com", "AdminPass1")
    coop = ensure_demo_cooperative(db, admin_id=admin.id)
    services = ensure_seed_services(db)
    service_id = services[0].id
    coop_id = coop.id
    db.close()
    return admin, coop_id, service_id


def sample_request_payload(service_id, description="Ceiling fan repair required urgently."):
    return {
        "service_id": service_id,
        "location": "Sector 62, Noida",
        "preferred_date": "2026-08-27",
        "preferred_time": "14:00",
        "description": description,
    }


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_customer_can_create_request():
    """1. Customer can create a service request."""
    _, coop_id, service_id = setup_base_data()
    register("cust1@test.com", role="CUSTOMER")
    ctoken = login("cust1@test.com").json()["access_token"]

    res = client.post(
        "/api/requests",
        json=sample_request_payload(service_id),
        headers=auth_header(ctoken),
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["customer_email"] == "cust1@test.com"
    assert data["status"] == "PENDING"
    assert data["cooperative_id"] == coop_id


def test_worker_cannot_create_request():
    """2. Worker cannot create a customer service request (403)."""
    _, _, service_id = setup_base_data()
    register("w1@test.com", role="WORKER")
    wtoken = login("w1@test.com").json()["access_token"]

    res = client.post(
        "/api/requests",
        json=sample_request_payload(service_id),
        headers=auth_header(wtoken),
    )
    assert res.status_code == 403, res.text


def test_admin_cannot_create_customer_request():
    """3. Admin cannot create a customer service request (403)."""
    _, _, service_id = setup_base_data()
    atoken = login("admin@test.com", "AdminPass1").json()["access_token"]

    res = client.post(
        "/api/requests",
        json=sample_request_payload(service_id),
        headers=auth_header(atoken),
    )
    assert res.status_code == 403, res.text


def test_service_must_exist():
    """4. Creating a request for a non-existent service returns 404."""
    setup_base_data()
    register("cust2@test.com", role="CUSTOMER")
    ctoken = login("cust2@test.com").json()["access_token"]

    res = client.post(
        "/api/requests",
        json=sample_request_payload(service_id=999999),
        headers=auth_header(ctoken),
    )
    assert res.status_code == 404, res.text


def test_inactive_service_rejected():
    """5. Creating a request for an inactive service returns 400."""
    from tests.conftest import TestingSessionLocal
    from app.models.service import Service

    _, _, service_id = setup_base_data()

    db = TestingSessionLocal()
    svc = db.query(Service).filter(Service.id == service_id).first()
    svc.is_active = False
    db.commit()
    db.close()

    register("cust3@test.com", role="CUSTOMER")
    ctoken = login("cust3@test.com").json()["access_token"]

    res = client.post(
        "/api/requests",
        json=sample_request_payload(service_id=service_id),
        headers=auth_header(ctoken),
    )
    assert res.status_code == 400, res.text


def test_description_required():
    """6. Empty description is rejected by validation (422)."""
    _, _, service_id = setup_base_data()
    register("cust4@test.com", role="CUSTOMER")
    ctoken = login("cust4@test.com").json()["access_token"]

    payload = sample_request_payload(service_id, description="   ")
    res = client.post("/api/requests", json=payload, headers=auth_header(ctoken))
    assert res.status_code == 422, res.text


def test_location_required():
    """7. Short/empty location is rejected by validation (422)."""
    _, _, service_id = setup_base_data()
    register("cust5@test.com", role="CUSTOMER")
    ctoken = login("cust5@test.com").json()["access_token"]

    payload = sample_request_payload(service_id)
    payload["location"] = " "
    res = client.post("/api/requests", json=payload, headers=auth_header(ctoken))
    assert res.status_code == 422, res.text


def test_date_validation():
    """8. Empty preferred date is rejected (422)."""
    _, _, service_id = setup_base_data()
    register("cust6@test.com", role="CUSTOMER")
    ctoken = login("cust6@test.com").json()["access_token"]

    payload = sample_request_payload(service_id)
    payload["preferred_date"] = ""
    res = client.post("/api/requests", json=payload, headers=auth_header(ctoken))
    assert res.status_code == 422, res.text


def test_time_validation():
    """9. Empty preferred time is rejected (422)."""
    _, _, service_id = setup_base_data()
    register("cust7@test.com", role="CUSTOMER")
    ctoken = login("cust7@test.com").json()["access_token"]

    payload = sample_request_payload(service_id)
    payload["preferred_time"] = ""
    res = client.post("/api/requests", json=payload, headers=auth_header(ctoken))
    assert res.status_code == 422, res.text


def test_customer_can_list_own_requests():
    """10. Customer can list their own requests via GET /api/requests/me."""
    _, _, service_id = setup_base_data()
    register("cust8@test.com", role="CUSTOMER")
    ctoken = login("cust8@test.com").json()["access_token"]

    client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken))
    client.post("/api/requests", json=sample_request_payload(service_id, description="Second request test."), headers=auth_header(ctoken))

    res = client.get("/api/requests/me", headers=auth_header(ctoken))
    assert res.status_code == 200, res.text
    requests = res.json()
    assert len(requests) == 2


def test_customer_cannot_see_another_customers_requests():
    """11. Customer only sees their own requests, not another customer's requests."""
    _, _, service_id = setup_base_data()
    register("custA@test.com", role="CUSTOMER")
    ctokenA = login("custA@test.com").json()["access_token"]

    register("custB@test.com", role="CUSTOMER")
    ctokenB = login("custB@test.com").json()["access_token"]

    client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctokenA))

    resB = client.get("/api/requests/me", headers=auth_header(ctokenB))
    assert resB.status_code == 200
    assert len(resB.json()) == 0


def test_customer_can_view_own_request():
    """12. Customer can fetch details of their own request by ID."""
    _, _, service_id = setup_base_data()
    register("cust12@test.com", role="CUSTOMER")
    ctoken = login("cust12@test.com").json()["access_token"]

    created = client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken)).json()
    req_id = created["id"]

    res = client.get(f"/api/requests/{req_id}", headers=auth_header(ctoken))
    assert res.status_code == 200, res.text
    assert res.json()["id"] == req_id


def test_customer_cannot_access_another_customers_request():
    """13. Attempting to fetch another customer's request returns 404 (does not reveal existence)."""
    _, _, service_id = setup_base_data()
    register("custX@test.com", role="CUSTOMER")
    ctokenX = login("custX@test.com").json()["access_token"]

    register("custY@test.com", role="CUSTOMER")
    ctokenY = login("custY@test.com").json()["access_token"]

    created = client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctokenX)).json()
    req_id = created["id"]

    res = client.get(f"/api/requests/{req_id}", headers=auth_header(ctokenY))
    assert res.status_code == 404, res.text


def test_customer_can_cancel_pending_request():
    """14. Customer can cancel a PENDING request via PATCH /api/requests/{id}/cancel."""
    _, _, service_id = setup_base_data()
    register("cust14@test.com", role="CUSTOMER")
    ctoken = login("cust14@test.com").json()["access_token"]

    created = client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken)).json()
    req_id = created["id"]

    res = client.patch(f"/api/requests/{req_id}/cancel", headers=auth_header(ctoken))
    assert res.status_code == 200, res.text
    assert res.json()["request"]["status"] == "CANCELLED"


def test_customer_cannot_cancel_completed_request():
    """15. Cancelling a non-PENDING (e.g. COMPLETED) request returns 400."""
    from tests.conftest import TestingSessionLocal
    from app.models.service_request import RequestStatus, ServiceRequest

    _, _, service_id = setup_base_data()
    register("cust15@test.com", role="CUSTOMER")
    ctoken = login("cust15@test.com").json()["access_token"]

    created = client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken)).json()
    req_id = created["id"]

    # Manually change status to COMPLETED in DB
    db = TestingSessionLocal()
    req = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    req.status = RequestStatus.COMPLETED
    db.commit()
    db.close()

    res = client.patch(f"/api/requests/{req_id}/cancel", headers=auth_header(ctoken))
    assert res.status_code == 400, res.text


def test_worker_cannot_access_admin_request_list():
    """16. Worker cannot access GET /api/requests (403)."""
    setup_base_data()
    register("w_no_req@test.com", role="WORKER")
    wtoken = login("w_no_req@test.com").json()["access_token"]

    res = client.get("/api/requests", headers=auth_header(wtoken))
    assert res.status_code == 403, res.text


def test_admin_can_view_cooperative_requests():
    """17. Admin can access GET /api/requests to view all cooperative requests."""
    _, _, service_id = setup_base_data()
    register("cust17@test.com", role="CUSTOMER")
    ctoken = login("cust17@test.com").json()["access_token"]

    client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken))

    atoken = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/requests", headers=auth_header(atoken))
    assert res.status_code == 200, res.text
    assert len(res.json()) == 1


def test_customer_id_comes_from_jwt():
    """18. Customer ID in created request matches the authenticated user ID from JWT."""
    _, _, service_id = setup_base_data()
    register("cust18@test.com", role="CUSTOMER")
    login_res = login("cust18@test.com").json()
    ctoken = login_res["access_token"]
    user_id = login_res["user"]["id"]

    created = client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken)).json()
    assert created["customer_id"] == user_id


def test_cooperative_id_comes_from_backend():
    """19. Cooperative ID is automatically populated by backend logic."""
    _, coop_id, service_id = setup_base_data()
    register("cust19@test.com", role="CUSTOMER")
    ctoken = login("cust19@test.com").json()["access_token"]

    created = client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken)).json()
    assert created["cooperative_id"] == coop_id


def test_request_status_defaults_to_pending():
    """20. Newly created service requests default to status PENDING."""
    _, _, service_id = setup_base_data()
    register("cust20@test.com", role="CUSTOMER")
    ctoken = login("cust20@test.com").json()["access_token"]

    created = client.post("/api/requests", json=sample_request_payload(service_id), headers=auth_header(ctoken)).json()
    assert created["status"] == "PENDING"
