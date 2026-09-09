"""
Tests for Worker Allocation, Bookings, and Job Workflow.

Validates allocation rules, authorization, conflict protection, status transitions,
cooperative workforce fairness updates, and security constraints.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.booking import Booking, BookingStatus
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from tests.conftest import TestingSessionLocal

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


def setup_booking_base():
    """Helper to seed base admin, coop, service, customer, worker, and request."""
    db = TestingSessionLocal()
    from app.services.auth import create_admin_if_absent, hash_password

    admin = create_admin_if_absent(db, name="Coop Admin", email="admin_b@test.com", password="AdminPass123")
    coop = Cooperative(name="Booking Coop", location="Noida", admin_id=admin.id)
    db.add(coop)
    db.commit()

    service = Service(name="Electrical Repairs & Maintenance", category="Electrical", description="Electrical repairs")
    db.add(service)
    db.commit()

    # Verified Worker in Coop
    w_user = User(name="Rahul Worker", email="worker_b@test.com", password_hash=hash_password("Worker@1234"), role=UserRole.WORKER)
    db.add(w_user)
    db.commit()

    worker = Worker(
        user_id=w_user.id,
        cooperative_id=coop.id,
        profession="Electrician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring"],
        experience_years=5,
        rating=4.8,
        total_jobs=5,
    )
    db.add(worker)
    db.commit()

    # Customer
    c_user = User(name="Asha Customer", email="customer_b@test.com", password_hash=hash_password("Customer@1234"), role=UserRole.CUSTOMER)
    db.add(c_user)
    db.commit()

    req = ServiceRequest(
        customer_id=c_user.id,
        service_id=service.id,
        cooperative_id=coop.id,
        description="Fix fan wiring",
        location="Sector 62, Noida",
        preferred_date="2026-08-30",
        preferred_time="14:00",
        status=RequestStatus.PENDING,
    )
    db.add(req)
    db.commit()

    req_id = req.id
    worker_id = worker.id
    w_user_id = w_user.id
    c_user_id = c_user.id
    db.close()
    return req_id, worker_id, w_user_id, c_user_id


# ── ALLOCATION TESTS (1-10) ──────────────────────────────────────────────────

def test_admin_can_allocate_worker():
    """1. Admin can allocate a verified worker to a pending request."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": worker_id, "amount": 500.0},
        headers=auth_header(atoken),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["request_id"] == req_id
    assert data["worker_id"] == worker_id
    assert data["status"] == "ASSIGNED"
    assert data["amount"] == 500.0


def test_customer_cannot_allocate_worker():
    """2. Customer receives 403 when trying to allocate worker."""
    req_id, worker_id, _, _ = setup_booking_base()
    ctoken = login("customer_b@test.com", "Customer@1234").json()["access_token"]

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": worker_id},
        headers=auth_header(ctoken),
    )
    assert res.status_code == 403


def test_worker_cannot_allocate_worker():
    """3. Worker receives 403 when trying to allocate worker."""
    req_id, worker_id, _, _ = setup_booking_base()
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": worker_id},
        headers=auth_header(wtoken),
    )
    assert res.status_code == 403


def test_unverified_worker_cannot_be_allocated():
    """4. Unverified/pending worker allocation is rejected."""
    req_id, _, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    db = TestingSessionLocal()
    from app.services.auth import hash_password
    u = User(name="Pending W", email="pending_w@test.com", password_hash=hash_password("Pass123"), role=UserRole.WORKER)
    db.add(u)
    db.commit()
    w = Worker(user_id=u.id, profession="Electrician", verification_status=VerificationStatus.PENDING, availability=AvailabilityStatus.AVAILABLE)
    db.add(w)
    db.commit()
    pw_id = w.id
    db.close()

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": pw_id},
        headers=auth_header(atoken),
    )
    assert res.status_code == 400
    assert "not verified" in res.json()["detail"]


def test_rejected_worker_cannot_be_allocated():
    """5. Rejected worker allocation is rejected."""
    req_id, _, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    db = TestingSessionLocal()
    from app.services.auth import hash_password
    u = User(name="Rejected W", email="rej_w@test.com", password_hash=hash_password("Pass123"), role=UserRole.WORKER)
    db.add(u)
    db.commit()
    w = Worker(user_id=u.id, profession="Electrician", verification_status=VerificationStatus.REJECTED, availability=AvailabilityStatus.AVAILABLE)
    db.add(w)
    db.commit()
    rw_id = w.id
    db.close()

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": rw_id},
        headers=auth_header(atoken),
    )
    assert res.status_code == 400


def test_unavailable_worker_cannot_be_allocated():
    """6. Unavailable worker allocation is rejected."""
    req_id, _, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    db = TestingSessionLocal()
    from app.services.auth import hash_password
    u = User(name="Unavail W", email="unavail_w@test.com", password_hash=hash_password("Pass123"), role=UserRole.WORKER)
    db.add(u)
    db.commit()
    w = Worker(user_id=u.id, profession="Electrician", verification_status=VerificationStatus.VERIFIED, availability=AvailabilityStatus.UNAVAILABLE)
    db.add(w)
    db.commit()
    uw_id = w.id
    db.close()

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": uw_id},
        headers=auth_header(atoken),
    )
    assert res.status_code == 400


def test_worker_from_another_cooperative_cannot_be_allocated():
    """7. Worker from another cooperative cannot be allocated."""
    req_id, _, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    db = TestingSessionLocal()
    from app.services.auth import hash_password
    other_coop = Cooperative(name="Other Coop", location="Delhi")
    db.add(other_coop)
    db.commit()

    u = User(name="Other W", email="other_w@test.com", password_hash=hash_password("Pass123"), role=UserRole.WORKER)
    db.add(u)
    db.commit()
    w = Worker(user_id=u.id, cooperative_id=other_coop.id, profession="Electrician", verification_status=VerificationStatus.VERIFIED, availability=AvailabilityStatus.AVAILABLE)
    db.add(w)
    db.commit()
    ow_id = w.id
    db.close()

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": ow_id},
        headers=auth_header(atoken),
    )
    assert res.status_code == 400


def test_invalid_worker_id_rejected():
    """8. Non-existent worker ID returns 404."""
    req_id, _, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": 999999},
        headers=auth_header(atoken),
    )
    assert res.status_code == 404


def test_invalid_request_id_rejected():
    """9. Non-existent request ID returns 404."""
    _, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    res = client.post(
        "/api/requests/999999/allocate",
        json={"worker_id": worker_id},
        headers=auth_header(atoken),
    )
    assert res.status_code == 404


def test_duplicate_active_booking_rejected():
    """10. Cannot allocate worker to request that already has an active booking."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    # First allocation
    res1 = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))
    assert res1.status_code == 201

    # Second allocation attempt on same request
    res2 = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"] or "status" in res2.json()["detail"]


# ── WORKER WORKFLOW TESTS (11-20) ─────────────────────────────────────────────

def test_worker_can_view_own_jobs():
    """11. Worker can view their assigned jobs."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))

    res = client.get("/api/bookings/worker", headers=auth_header(wtoken))
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["worker_id"] == worker_id
    assert data[0]["status"] == "ASSIGNED"


def test_worker_cannot_view_another_workers_jobs():
    """12. Worker only receives their own assigned jobs."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))

    # Register worker 2
    register("other_w2@test.com", role="WORKER")
    w2token = login("other_w2@test.com").json()["access_token"]

    res = client.get("/api/bookings/worker", headers=auth_header(w2token))
    assert res.status_code == 200
    assert res.json() == []


def test_worker_can_accept_assigned_job():
    """13. Worker can accept an assigned job (ASSIGNED -> ACCEPTED)."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    res = client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken))
    assert res.status_code == 200
    assert res.json()["status"] == "ACCEPTED"


def test_worker_can_reject_assigned_job():
    """14. Worker can reject an assigned job (ASSIGNED -> REJECTED)."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    res = client.patch(f"/api/bookings/{booking_id}/reject", headers=auth_header(wtoken))
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"


def test_rejected_job_returns_request_to_pending():
    """15. Worker rejecting a job resets ServiceRequest status to PENDING for re-allocation."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    client.patch(f"/api/bookings/{booking_id}/reject", headers=auth_header(wtoken))

    # Check request status
    db = TestingSessionLocal()
    req = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    assert req.status == RequestStatus.PENDING
    db.close()


def test_worker_can_start_accepted_job():
    """16. Worker can start an accepted job (ACCEPTED -> IN_PROGRESS)."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken))
    res = client.patch(f"/api/bookings/{booking_id}/start", headers=auth_header(wtoken))

    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"


def test_worker_cannot_start_assigned_job_directly():
    """17. Worker cannot start an assigned job directly without accepting first."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    res = client.patch(f"/api/bookings/{booking_id}/start", headers=auth_header(wtoken))
    assert res.status_code == 400


def test_worker_can_complete_in_progress_job():
    """18. Worker can complete an in-progress job (IN_PROGRESS -> COMPLETED)."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken))
    client.patch(f"/api/bookings/{booking_id}/start", headers=auth_header(wtoken))
    res = client.patch(f"/api/bookings/{booking_id}/complete", headers=auth_header(wtoken))

    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"


def test_worker_cannot_complete_accepted_job_directly():
    """19. Worker cannot mark an accepted job completed without starting it first."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken))
    res = client.patch(f"/api/bookings/{booking_id}/complete", headers=auth_header(wtoken))

    assert res.status_code == 400


def test_worker_total_jobs_increments_after_completion():
    """20. Worker total_jobs counter is incremented by 1 when job is completed."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    db = TestingSessionLocal()
    w_initial = db.query(Worker).filter(Worker.id == worker_id).first()
    initial_jobs = w_initial.total_jobs
    db.close()

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken))
    client.patch(f"/api/bookings/{booking_id}/start", headers=auth_header(wtoken))
    client.patch(f"/api/bookings/{booking_id}/complete", headers=auth_header(wtoken))

    db2 = TestingSessionLocal()
    w_updated = db2.query(Worker).filter(Worker.id == worker_id).first()
    assert w_updated.total_jobs == initial_jobs + 1
    db2.close()


# ── CUSTOMER WORKFLOW TESTS (21-24) ───────────────────────────────────────────

def test_customer_can_view_own_booking():
    """21. Customer can view bookings associated with their requests."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    ctoken = login("customer_b@test.com", "Customer@1234").json()["access_token"]

    client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))

    res = client.get("/api/bookings/me", headers=auth_header(ctoken))
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["worker_name"] == "Rahul Worker"


def test_customer_cannot_view_another_customers_booking():
    """22. Customer receives 403 if attempting to view another customer's booking directly."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    register("cust_other@test.com", role="CUSTOMER")
    c2token = login("cust_other@test.com").json()["access_token"]

    res = client.get(f"/api/bookings/{booking_id}", headers=auth_header(c2token))
    assert res.status_code == 403


def test_customer_sees_worker_assignment():
    """23. Customer booking view includes assigned worker name & details."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    ctoken = login("customer_b@test.com", "Customer@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    res = client.get(f"/api/bookings/{booking_id}", headers=auth_header(ctoken))
    assert res.status_code == 200
    data = res.json()
    assert data["worker_name"] == "Rahul Worker"
    assert data["service_name"] == "Electrical Repairs & Maintenance"


def test_customer_cannot_change_booking_status():
    """24. Customer receives 403 when calling worker status transition endpoints."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    ctoken = login("customer_b@test.com", "Customer@1234").json()["access_token"]

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc_res["id"]

    res = client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(ctoken))
    assert res.status_code == 403


# ── ADMIN WORKFLOW TESTS (25-26) ─────────────────────────────────────────────

def test_admin_can_view_cooperative_bookings():
    """25. Admin can view all cooperative bookings."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))

    res = client.get("/api/bookings", headers=auth_header(atoken))
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_admin_cannot_allocate_worker_from_another_cooperative():
    """26. Admin cannot allocate a worker belonging to a different cooperative."""
    req_id, _, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    db = TestingSessionLocal()
    from app.services.auth import hash_password
    other_coop = Cooperative(name="Other Coop", location="Delhi")
    db.add(other_coop)
    db.commit()

    u = User(name="Other Coop W", email="ocw@test.com", password_hash=hash_password("Worker@1234"), role=UserRole.WORKER)
    db.add(u)
    db.commit()
    w = Worker(user_id=u.id, cooperative_id=other_coop.id, profession="Electrician", verification_status=VerificationStatus.VERIFIED, availability=AvailabilityStatus.AVAILABLE)
    db.add(w)
    db.commit()
    other_w_id = w.id
    db.close()

    res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": other_w_id},
        headers=auth_header(atoken),
    )
    assert res.status_code == 400


# ── STATUS TRANSITIONS TESTS (27-30) ──────────────────────────────────────────

def test_valid_status_transitions():
    """27. Full valid status transition lifecycle works cleanly."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    # 1. Allocate (PENDING -> ASSIGNED)
    alloc = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc["id"]
    assert alloc["status"] == "ASSIGNED"

    # 2. Accept (ASSIGNED -> ACCEPTED)
    acc = client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken)).json()
    assert acc["status"] == "ACCEPTED"

    # 3. Start (ACCEPTED -> IN_PROGRESS)
    st = client.patch(f"/api/bookings/{booking_id}/start", headers=auth_header(wtoken)).json()
    assert st["status"] == "IN_PROGRESS"

    # 4. Complete (IN_PROGRESS -> COMPLETED)
    cmp = client.patch(f"/api/bookings/{booking_id}/complete", headers=auth_header(wtoken)).json()
    assert cmp["status"] == "COMPLETED"


def test_invalid_status_transitions_rejected():
    """28. Invalid status transition attempts are rejected with 400 Bad Request."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc["id"]

    # Try ASSIGNED -> COMPLETED directly
    res = client.patch(f"/api/bookings/{booking_id}/complete", headers=auth_header(wtoken))
    assert res.status_code == 400


def test_completed_booking_cannot_be_modified():
    """29. Completed booking cannot undergo further status changes."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc["id"]

    client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken))
    client.patch(f"/api/bookings/{booking_id}/start", headers=auth_header(wtoken))
    client.patch(f"/api/bookings/{booking_id}/complete", headers=auth_header(wtoken))

    # Try ACCEPT again
    res = client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(wtoken))
    assert res.status_code == 400


def test_rejected_booking_cannot_be_completed_directly():
    """30. Rejected booking cannot be transitioned to completed directly."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    alloc = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc["id"]

    client.patch(f"/api/bookings/{booking_id}/reject", headers=auth_header(wtoken))

    res = client.patch(f"/api/bookings/{booking_id}/complete", headers=auth_header(wtoken))
    assert res.status_code == 400


# ── CONFLICT PROTECTION TESTS (31) ───────────────────────────────────────────

def test_same_worker_cannot_have_two_active_jobs_at_same_date_time():
    """31. Allocation fails if worker already has an active job scheduled at the exact same date & time."""
    req_id, worker_id, _, c_user_id = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    # Allocate job 1
    res1 = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))
    assert res1.status_code == 201

    # Create request 2 for same customer, same date (2026-08-30) and same time (14:00)
    db = TestingSessionLocal()
    from app.models.cooperative import Cooperative
    coop = db.query(Cooperative).filter(Cooperative.admin_id == 1).first()
    service = db.query(Service).first()
    coop_id = coop.id if coop else 1
    service_id = service.id if service else 1

    req2 = ServiceRequest(
        customer_id=c_user_id,
        service_id=service_id,
        cooperative_id=coop_id,
        description="Conflict job test",
        location="Sector 62, Noida",
        preferred_date="2026-08-30",
        preferred_time="14:00",
        status=RequestStatus.PENDING,
    )
    db.add(req2)
    db.commit()
    req2_id = req2.id
    db.close()

    # Attempt to allocate same worker to request 2 -> Conflict!
    res2 = client.post(f"/api/requests/{req2_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))
    assert res2.status_code == 400
    assert "already has an active job" in res2.json()["detail"]


# ── SECURITY & IDENTITIES TESTS (32-35) ───────────────────────────────────────

def test_jwt_identity_determines_customer():
    """32. Customer identity comes strictly from JWT access token."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    ctoken = login("customer_b@test.com", "Customer@1234").json()["access_token"]

    client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))

    res = client.get("/api/bookings/me", headers=auth_header(ctoken))
    assert res.status_code == 200
    data = res.json()
    assert data[0]["customer_name"] == "Asha Customer"


def test_jwt_identity_determines_worker():
    """33. Worker identity comes strictly from JWT access token."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]
    wtoken = login("worker_b@test.com", "Worker@1234").json()["access_token"]

    client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken))

    res = client.get("/api/bookings/worker", headers=auth_header(wtoken))
    assert res.status_code == 200
    data = res.json()
    assert data[0]["worker_name"] == "Rahul Worker"


def test_frontend_cannot_override_worker_ownership():
    """34. Worker cannot accept/reject bookings assigned to other workers."""
    req_id, worker_id, _, _ = setup_booking_base()
    atoken = login("admin_b@test.com", "AdminPass123").json()["access_token"]

    alloc = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(atoken)).json()
    booking_id = alloc["id"]

    # Register worker 2
    register("other_w3@test.com", role="WORKER")
    w2token = login("other_w3@test.com").json()["access_token"]

    res = client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(w2token))
    assert res.status_code == 403


def test_frontend_cannot_override_cooperative_ownership():
    """35. Admin cannot view or allocate requests outside their cooperative."""
    db = TestingSessionLocal()
    from app.services.auth import create_admin_if_absent
    admin2 = create_admin_if_absent(db, name="Other Admin", email="admin_other@test.com", password="AdminPass123")
    coop2 = Cooperative(name="Other Coop 2", location="Delhi", admin_id=admin2.id)
    db.add(coop2)
    db.commit()
    a2token = login("admin_other@test.com", "AdminPass123").json()["access_token"]

    req_id, worker_id, _, _ = setup_booking_base()

    # Attempt allocation by Admin 2 on Coop 1's request
    res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(a2token))
    assert res.status_code == 400
    db.close()
