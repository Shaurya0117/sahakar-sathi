"""
Worker profile tests — 16 required cases.

Fixtures and DB override are provided by conftest.py.

Run:
    cd backend
    pytest tests/test_workers.py -v
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def register(email, password="Password1", role="WORKER", name="Test Worker"):
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


def make_admin():
    """Create an admin account directly via the service layer."""
    from tests.conftest import TestingSessionLocal
    from app.services.auth import create_admin_if_absent
    db = TestingSessionLocal()
    create_admin_if_absent(db, "Admin", "admin@test.com", "AdminPass1")
    db.close()


def worker_token():
    """Register + login a worker; return (token, user_id)."""
    register("worker@test.com")
    res = login("worker@test.com")
    data = res.json()
    return data["access_token"], data["user"]["id"]


def customer_token():
    register("customer@test.com", role="CUSTOMER", name="Test Customer")
    res = login("customer@test.com")
    data = res.json()
    return data["access_token"], data["user"]["id"]


def admin_token():
    make_admin()
    res = login("admin@test.com", password="AdminPass1")
    data = res.json()
    return data["access_token"], data["user"]["id"]


SAMPLE_PROFILE = {
    "profession": "Electrician",
    "skills": ["Wiring", "Fan Repair", "Switch Repair"],
    "experience_years": 5,
    "location": "Sector 62, Noida",
    "availability": "AVAILABLE",
    "availability_description": "Mon-Sat 9AM-6PM",
}


def create_profile(token, payload=None):
    if payload is None:
        payload = SAMPLE_PROFILE
    return client.post(
        "/api/workers/me",
        json=payload,
        headers=auth_header(token),
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_worker_can_create_profile():
    """1. A WORKER user can create their profile."""
    token, _ = worker_token()
    res = create_profile(token)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["profession"] == "Electrician"
    assert data["skills"] == ["Wiring", "Fan Repair", "Switch Repair"]
    assert data["experience_years"] == 5
    assert data["location"] == "Sector 62, Noida"
    assert data["email"] == "worker@test.com"


def test_customer_cannot_create_worker_profile():
    """2. A CUSTOMER user is forbidden from creating a worker profile."""
    token, _ = customer_token()
    res = create_profile(token)
    assert res.status_code == 403, res.text


def test_admin_cannot_create_worker_profile():
    """3. An ADMIN user is forbidden from creating a worker profile."""
    token, _ = admin_token()
    res = create_profile(token)
    assert res.status_code == 403, res.text


def test_worker_can_retrieve_own_profile():
    """4. A WORKER can retrieve their profile via GET /api/workers/me."""
    token, _ = worker_token()
    create_profile(token)

    res = client.get("/api/workers/me", headers=auth_header(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["profession"] == "Electrician"
    assert "password_hash" not in data
    assert "password" not in data


def test_worker_can_update_own_profile():
    """5. A WORKER can update their profile."""
    token, _ = worker_token()
    create_profile(token)

    res = client.put(
        "/api/workers/me",
        json={"profession": "Plumber", "experience_years": 3},
        headers=auth_header(token),
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["profession"] == "Plumber"
    assert data["experience_years"] == 3
    # Unchanged fields should be preserved
    assert data["location"] == "Sector 62, Noida"


def test_worker_profile_linked_to_correct_user():
    """6. The worker profile's user_id matches the authenticated user's id."""
    token, user_id = worker_token()
    create_profile(token)

    res = client.get("/api/workers/me", headers=auth_header(token))
    assert res.status_code == 200, res.text
    assert res.json()["user_id"] == user_id


def test_duplicate_worker_profile_rejected():
    """7. Creating a second profile for the same worker returns 409."""
    token, _ = worker_token()
    create_profile(token)

    res = create_profile(token)
    assert res.status_code == 409, res.text


def test_default_verification_status_is_pending():
    """8. A newly created worker profile has verification_status PENDING."""
    token, _ = worker_token()
    res = create_profile(token)
    assert res.status_code == 201, res.text
    assert res.json()["verification_status"] == "PENDING"


def test_worker_cannot_modify_verification_status():
    """9. A worker cannot change verification_status via the update endpoint."""
    token, _ = worker_token()
    create_profile(token)

    # WorkerUpdateRequest doesn't include verification_status — extra fields ignored by Pydantic
    res = client.put(
        "/api/workers/me",
        json={"verification_status": "VERIFIED"},
        headers=auth_header(token),
    )
    # Either 200 (field ignored) or 422 (Pydantic rejects unknown field)
    assert res.status_code in (200, 422)

    # Confirm via GET — must still be PENDING
    get_res = client.get("/api/workers/me", headers=auth_header(token))
    assert get_res.json()["verification_status"] == "PENDING"


def test_worker_cannot_modify_rating():
    """10. A worker cannot change their rating."""
    token, _ = worker_token()
    create_profile(token)

    client.put(
        "/api/workers/me",
        json={"rating": 5.0},
        headers=auth_header(token),
    )
    get_res = client.get("/api/workers/me", headers=auth_header(token))
    assert get_res.json()["rating"] == 0.0


def test_worker_cannot_modify_total_jobs():
    """11. A worker cannot change their total_jobs."""
    token, _ = worker_token()
    create_profile(token)

    client.put(
        "/api/workers/me",
        json={"total_jobs": 999},
        headers=auth_header(token),
    )
    get_res = client.get("/api/workers/me", headers=auth_header(token))
    assert get_res.json()["total_jobs"] == 0


def test_admin_can_verify_worker():
    """12. An ADMIN can set a worker's verification_status to VERIFIED."""
    wtoken, _ = worker_token()
    create_profile(wtoken)

    profile = client.get("/api/workers/me", headers=auth_header(wtoken)).json()
    worker_id = profile["id"]

    atoken, _ = admin_token()
    res = client.patch(
        f"/api/workers/{worker_id}/verification",
        json={"status": "VERIFIED"},
        headers=auth_header(atoken),
    )
    assert res.status_code == 200, res.text
    assert res.json()["verification_status"] == "VERIFIED"


def test_admin_can_reject_worker():
    """13. An ADMIN can set a worker's verification_status to REJECTED."""
    wtoken, _ = worker_token()
    create_profile(wtoken)

    profile = client.get("/api/workers/me", headers=auth_header(wtoken)).json()
    worker_id = profile["id"]

    atoken, _ = admin_token()
    res = client.patch(
        f"/api/workers/{worker_id}/verification",
        json={"status": "REJECTED"},
        headers=auth_header(atoken),
    )
    assert res.status_code == 200, res.text
    assert res.json()["verification_status"] == "REJECTED"


def test_worker_cannot_verify_themselves():
    """14. A worker cannot call the verification endpoint (403)."""
    token, _ = worker_token()
    create_profile(token)

    profile = client.get("/api/workers/me", headers=auth_header(token)).json()
    worker_id = profile["id"]

    res = client.patch(
        f"/api/workers/{worker_id}/verification",
        json={"status": "VERIFIED"},
        headers=auth_header(token),
    )
    assert res.status_code == 403, res.text


def test_customer_cannot_verify_worker():
    """15. A customer cannot call the verification endpoint (403)."""
    wtoken, _ = worker_token()
    create_profile(wtoken)

    profile = client.get("/api/workers/me", headers=auth_header(wtoken)).json()
    worker_id = profile["id"]

    ctoken, _ = customer_token()
    res = client.patch(
        f"/api/workers/{worker_id}/verification",
        json={"status": "VERIFIED"},
        headers=auth_header(ctoken),
    )
    assert res.status_code == 403, res.text


def test_profile_completion_calculated_correctly():
    """16. Profile completion is calculated server-side based on filled fields.

    5 completion fields: profession, experience_years, location, skills, availability.
    Full profile = 100%. Skills empty + location missing = 3/5 = 60%.
    """
    token, _ = worker_token()

    # Complete profile — all 5 fields filled
    res = create_profile(token, payload=SAMPLE_PROFILE)
    assert res.status_code == 201, res.text
    assert res.json()["profile_completion"] == 100

    # Partial profile: skills empty + location omitted → 3/5 = 60%
    register("worker2@test.com", name="Worker Two")
    token2 = login("worker2@test.com").json()["access_token"]
    res2 = create_profile(token2, payload={
        "profession": "Plumber",        # ✓ counts
        "skills": [],                   # ✗ empty — does NOT count
        "experience_years": 2,          # ✓ counts
        # location omitted — NOT counted
        "availability": "AVAILABLE",    # ✓ counts (default present)
    })
    assert res2.status_code == 201, res2.text
    # profession(1) + experience(1) + availability(1) = 3/5 = 60%
    assert res2.json()["profile_completion"] == 60
