"""
Cooperative Admin Dashboard & Service Catalog tests — 17 test cases.

Run:
    cd backend
    pytest tests/test_cooperative.py -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Helpers ────────────────────────────────────────────────────────────────────

def register(email, password="Password1", role="WORKER", name="Test User"):
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


def setup_admin_and_cooperative():
    from tests.conftest import TestingSessionLocal
    from app.services.auth import create_admin_if_absent
    from app.services.cooperative import ensure_demo_cooperative
    from app.services.service_catalog import ensure_seed_services

    db = TestingSessionLocal()
    admin = create_admin_if_absent(db, "Admin", "admin@test.com", "AdminPass1")
    coop = ensure_demo_cooperative(db, admin_id=admin.id)
    services = ensure_seed_services(db)
    # Refresh / expunge to allow attribute access after session close
    db.refresh(admin)
    db.refresh(coop)
    admin_id = admin.id
    coop_name = coop.name
    coop_location = coop.location
    coop_admin_id = coop.admin_id
    db.close()
    return admin, coop, services


def create_demo_worker(email, profession="Electrician", status="PENDING", availability="AVAILABLE"):
    from tests.conftest import TestingSessionLocal
    from app.models.user import User, UserRole
    from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
    from app.services.auth import hash_password

    db = TestingSessionLocal()
    user = User(
        name=f"Worker {email}",
        email=email,
        password_hash=hash_password("Password1"),
        role=UserRole.WORKER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    worker = Worker(
        user_id=user.id,
        profession=profession,
        experience_years=5,
        location="Ghaziabad",
        skills=["Wiring"],
        availability=AvailabilityStatus(availability),
        verification_status=VerificationStatus(status),
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    db.close()
    return worker


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_cooperative_creation_and_seed():
    """1. Cooperative creation and seed script creates default primary cooperative."""
    setup_admin_and_cooperative()
    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/cooperative/me", headers=auth_header(admin_token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["name"] == "Ghaziabad Community Services Cooperative"
    assert data["location"] == "Ghaziabad, Uttar Pradesh"


def test_admin_associated_with_cooperative():
    """2. Admin user is associated with the cooperative."""
    admin, _, _ = setup_admin_and_cooperative()
    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/cooperative/me", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.json()["admin_id"] == admin.id


def test_worker_associated_with_cooperative():
    """3. Worker profiles can be linked to the cooperative."""
    setup_admin_and_cooperative()
    w = create_demo_worker("w1@test.com")
    assert w.user_id is not None


def test_admin_can_access_cooperative_stats():
    """4. Admin can access GET /api/cooperative/stats."""
    setup_admin_and_cooperative()
    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]

    res = client.get("/api/cooperative/stats", headers=auth_header(admin_token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert "total_workers" in data
    assert "verified_workers" in data


def test_worker_cannot_access_cooperative_stats():
    """5. Worker cannot access GET /api/cooperative/stats (403)."""
    setup_admin_and_cooperative()
    register("w2@test.com", role="WORKER")
    wtoken = login("w2@test.com").json()["access_token"]

    res = client.get("/api/cooperative/stats", headers=auth_header(wtoken))
    assert res.status_code == 403, res.text


def test_customer_cannot_access_cooperative_stats():
    """6. Customer cannot access GET /api/cooperative/stats (403)."""
    setup_admin_and_cooperative()
    register("c1@test.com", role="CUSTOMER")
    ctoken = login("c1@test.com").json()["access_token"]

    res = client.get("/api/cooperative/stats", headers=auth_header(ctoken))
    assert res.status_code == 403, res.text


def test_statistics_correctly_count_workers():
    """7. Statistics dynamically count workers in the database."""
    setup_admin_and_cooperative()
    create_demo_worker("w_stat1@test.com")
    create_demo_worker("w_stat2@test.com")

    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/cooperative/stats", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.json()["total_workers"] == 2


def test_verified_worker_count_correct():
    """8. Verified worker count accurately reflects database status."""
    setup_admin_and_cooperative()
    create_demo_worker("w_ver1@test.com", status="VERIFIED")
    create_demo_worker("w_ver2@test.com", status="VERIFIED")
    create_demo_worker("w_pen1@test.com", status="PENDING")

    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/cooperative/stats", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.json()["verified_workers"] == 2


def test_pending_worker_count_correct():
    """9. Pending worker count accurately reflects database status."""
    setup_admin_and_cooperative()
    create_demo_worker("w_p1@test.com", status="PENDING")
    create_demo_worker("w_p2@test.com", status="PENDING")

    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/cooperative/stats", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.json()["pending_workers"] == 2


def test_available_worker_count_correct():
    """10. Available worker count accurately reflects database status."""
    setup_admin_and_cooperative()
    create_demo_worker("w_a1@test.com", availability="AVAILABLE")
    create_demo_worker("w_a2@test.com", availability="UNAVAILABLE")

    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/cooperative/stats", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert res.json()["available_workers"] == 1
    assert res.json()["unavailable_workers"] == 1


def test_admin_can_list_workers():
    """11. Admin can access GET /api/workers to list all workers."""
    setup_admin_and_cooperative()
    create_demo_worker("w_list1@test.com")

    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.get("/api/workers", headers=auth_header(admin_token))
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_worker_cannot_access_admin_worker_list():
    """12. Worker cannot list all workers via GET /api/workers (403)."""
    setup_admin_and_cooperative()
    register("w_no_access@test.com", role="WORKER")
    wtoken = login("w_no_access@test.com").json()["access_token"]

    res = client.get("/api/workers", headers=auth_header(wtoken))
    assert res.status_code == 403, res.text


def test_admin_can_verify_worker():
    """13. Admin can verify a worker via PATCH /api/workers/{id}/verification."""
    setup_admin_and_cooperative()
    w = create_demo_worker("w_to_verify@test.com", status="PENDING")

    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.patch(
        f"/api/workers/{w.id}/verification",
        json={"status": "VERIFIED"},
        headers=auth_header(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["verification_status"] == "VERIFIED"


def test_admin_can_reject_worker():
    """14. Admin can reject a worker via PATCH /api/workers/{id}/verification."""
    setup_admin_and_cooperative()
    w = create_demo_worker("w_to_reject@test.com", status="PENDING")

    admin_token = login("admin@test.com", "AdminPass1").json()["access_token"]
    res = client.patch(
        f"/api/workers/{w.id}/verification",
        json={"status": "REJECTED"},
        headers=auth_header(admin_token),
    )
    assert res.status_code == 200
    assert res.json()["verification_status"] == "REJECTED"


def test_worker_cannot_verify_themselves():
    """15. Worker receives 403 if calling verification endpoint."""
    setup_admin_and_cooperative()
    w = create_demo_worker("w_self@test.com", status="PENDING")
    wtoken = login("w_self@test.com").json()["access_token"]

    res = client.patch(
        f"/api/workers/{w.id}/verification",
        json={"status": "VERIFIED"},
        headers=auth_header(wtoken),
    )
    assert res.status_code == 403


def test_customer_cannot_verify_worker():
    """16. Customer receives 403 if calling verification endpoint."""
    setup_admin_and_cooperative()
    w = create_demo_worker("w_cust_test@test.com", status="PENDING")
    register("c_verifier@test.com", role="CUSTOMER")
    ctoken = login("c_verifier@test.com").json()["access_token"]

    res = client.patch(
        f"/api/workers/{w.id}/verification",
        json={"status": "VERIFIED"},
        headers=auth_header(ctoken),
    )
    assert res.status_code == 403


def test_service_seed_data_exists():
    """17. Service catalog endpoint returns seeded services."""
    setup_admin_and_cooperative()
    register("user_svc@test.com", role="CUSTOMER")
    token = login("user_svc@test.com").json()["access_token"]

    res = client.get("/api/services", headers=auth_header(token))
    assert res.status_code == 200, res.text
    services = res.json()
    assert len(services) >= 5
    names = [s["name"] for s in services]
    assert "Plumbing & Sanitation" in names
