import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.auth import hash_password
from app.services.proof_verification import (
    get_daily_nonce,
    build_canonical,
    compute_proof_tag,
    derive_completion_code,
)
from tests.conftest import TestingSessionLocal

client = TestClient(app)
IST = timezone(timedelta(hours=5, minutes=30))


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def login_token(email, password="Password123"):
    res = client.post("/api/auth/login", data={"username": email, "password": password})
    return res.json()["access_token"]


def create_test_worker(db, email_prefix, coop_id):
    u = User(
        name=f"Worker {email_prefix}",
        email=f"{email_prefix}@test.com",
        password_hash=hash_password("Password123"),
        role=UserRole.WORKER
    )
    db.add(u)
    db.commit()
    w = Worker(
        user_id=u.id,
        cooperative_id=coop_id,
        profession="Electrician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring"],
        experience_years=3,
        rating=4.5,
        total_jobs=0,
    )
    db.add(w)
    db.commit()
    return u, w


def setup_in_progress_job(service_lat=None, service_lon=None):
    """Sets up an IN_PROGRESS job and returns (booking_id, worker_id, worker_token, customer_token, req_id)"""
    db = TestingSessionLocal()
    uid = uuid.uuid4().hex[:8]

    # Admin & Coop
    admin = User(
        name=f"Admin {uid}",
        email=f"admin_{uid}@test.com",
        password_hash=hash_password("Password123"),
        role=UserRole.ADMIN
    )
    db.add(admin)
    db.commit()

    coop = Cooperative(name=f"Coop {uid}", location="Noida", admin_id=admin.id)
    db.add(coop)
    db.commit()

    # Service
    srv = Service(name=f"Service {uid}", category="Electrical", description="Test srv")
    db.add(srv)
    db.commit()

    # Customer
    cust = User(
        name=f"Cust {uid}",
        email=f"cust_{uid}@test.com",
        password_hash=hash_password("Password123"),
        role=UserRole.CUSTOMER
    )
    db.add(cust)
    db.commit()

    # Worker
    w_user, worker = create_test_worker(db, f"w_{uid}", coop.id)

    # ServiceRequest
    req = ServiceRequest(
        customer_id=cust.id,
        service_id=srv.id,
        cooperative_id=coop.id,
        description="Fix issue",
        location="Sector 62, Noida",
        latitude=service_lat,
        longitude=service_lon,
        preferred_date="2026-10-24",
        preferred_time="10:00",
        status=RequestStatus.PENDING,
    )
    db.add(req)
    db.commit()

    req_id = req.id
    worker_id = worker.id
    w_email = w_user.email
    c_email = cust.email
    a_email = admin.email
    db.close()

    a_tok = login_token(a_email)
    w_tok = login_token(w_email)
    c_tok = login_token(c_email)

    # Allocate
    alloc_res = client.post(
        f"/api/requests/{req_id}/allocate",
        json={"worker_id": worker_id},
        headers=auth_header(a_tok)
    ).json()
    booking_id = alloc_res["id"]

    # Transition: ACCEPT -> ARRIVE -> START
    client.patch(f"/api/bookings/{booking_id}/accept", headers=auth_header(w_tok))
    client.patch(f"/api/bookings/{booking_id}/arrive", headers=auth_header(w_tok))
    client.patch(f"/api/bookings/{booking_id}/start", headers=auth_header(w_tok))

    return booking_id, worker_id, w_tok, c_tok, req_id


# 1. Nonce differs per worker
def test_nonce_differs_per_worker():
    n1 = get_daily_nonce(101, "2026-10-24")
    n2 = get_daily_nonce(102, "2026-10-24")
    assert n1 != n2


# 2. Nonce differs per day
def test_nonce_differs_per_day():
    n1 = get_daily_nonce(101, "2026-10-24")
    n2 = get_daily_nonce(101, "2026-10-25")
    assert n1 != n2


# 3. Nonce same within day
def test_nonce_same_within_day():
    n1 = get_daily_nonce(101, "2026-10-24")
    n2 = get_daily_nonce(101, "2026-10-24")
    assert n1 == n2


# 4. Tampered field gives tag mismatch
def test_tampered_field_gives_tag_mismatch():
    booking_id, worker_id, w_tok, c_tok, _ = setup_in_progress_job()
    code = client.get(f"/api/bookings/{booking_id}/completion-code", headers=auth_header(c_tok)).json()["code"]
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, today_str)

    photo_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f506172839a4b5c6d7e8f9a"
    canonical = build_canonical(booking_id, worker_id, photo_hash, 28.61, 77.20, "2026-10-24T12:00:00Z", today_str, code)
    tag = compute_proof_tag(nonce, canonical)

    # Tamper with lat
    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": 28.62, # changed!
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": code,
        "tag": tag,
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "E_TAG_MISMATCH"


# 5. Reused tag gives tag reused
def test_reused_tag_gives_tag_reused():
    booking_id1, worker_id1, w_tok1, c_tok1, _ = setup_in_progress_job()
    code1 = client.get(f"/api/bookings/{booking_id1}/completion-code", headers=auth_header(c_tok1)).json()["code"]
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce1 = get_daily_nonce(worker_id1, today_str)

    photo_hash1 = "1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff"
    canonical1 = build_canonical(booking_id1, worker_id1, photo_hash1, 28.61, 77.20, "2026-10-24T12:00:00Z", today_str, code1)
    tag1 = compute_proof_tag(nonce1, canonical1)

    payload1 = {
        "proof_of_work_hash": photo_hash1,
        "lat": 28.61,
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": code1,
        "tag": tag1,
    }
    res1 = client.patch(f"/api/bookings/{booking_id1}/complete", json=payload1, headers=auth_header(w_tok1))
    assert res1.status_code == 200

    # Submitting the same bundle again triggers E_TAG_REUSED
    res2 = client.patch(f"/api/bookings/{booking_id1}/complete", json=payload1, headers=auth_header(w_tok1))
    assert res2.status_code == 400
    assert res2.json()["detail"]["code"] == "E_TAG_REUSED"


# 6. Hash within 6 bits gives duplicate
def test_hash_within_6_bits_gives_duplicate():
    booking_id1, worker_id1, w_tok1, c_tok1, _ = setup_in_progress_job()
    code1 = client.get(f"/api/bookings/{booking_id1}/completion-code", headers=auth_header(c_tok1)).json()["code"]
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce1 = get_daily_nonce(worker_id1, today_str)

    base_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    canonical1 = build_canonical(booking_id1, worker_id1, base_hash, 28.61, 77.20, "2026-10-24T12:00:00Z", today_str, code1)
    tag1 = compute_proof_tag(nonce1, canonical1)

    payload1 = {
        "proof_of_work_hash": base_hash,
        "lat": 28.61,
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": code1,
        "tag": tag1,
    }
    res1 = client.patch(f"/api/bookings/{booking_id1}/complete", json=payload1, headers=auth_header(w_tok1))
    assert res1.status_code == 200

    # Job 2: Hash with 2 bits flipped (Hamming dist = 2 <= 6)
    similar_hash = "0000000000000000000000000000000000000000000000000000000000000003"
    booking_id2, worker_id2, w_tok2, c_tok2, _ = setup_in_progress_job()
    code2 = client.get(f"/api/bookings/{booking_id2}/completion-code", headers=auth_header(c_tok2)).json()["code"]
    nonce2 = get_daily_nonce(worker_id2, today_str)
    canonical2 = build_canonical(booking_id2, worker_id2, similar_hash, 28.61, 77.20, "2026-10-24T12:00:00Z", today_str, code2)
    tag2 = compute_proof_tag(nonce2, canonical2)

    payload2 = {
        "proof_of_work_hash": similar_hash,
        "lat": 28.61,
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": code2,
        "tag": tag2,
    }
    res2 = client.patch(f"/api/bookings/{booking_id2}/complete", json=payload2, headers=auth_header(w_tok2))
    assert res2.status_code == 400
    assert res2.json()["detail"]["code"] == "E_HASH_DUPLICATE"


# 7. GPS beyond 500m gives gps far
def test_gps_beyond_500m_gives_gps_far():
    booking_id, worker_id, w_tok, c_tok, _ = setup_in_progress_job(service_lat=28.61234, service_lon=77.20987)
    code = client.get(f"/api/bookings/{booking_id}/completion-code", headers=auth_header(c_tok)).json()["code"]
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, today_str)

    far_lat, far_lon = 28.75000, 77.20987
    photo_hash = "222233334444555566667777888899990000aaaabbbbccccddddeeeeffff2222"
    canonical = build_canonical(booking_id, worker_id, photo_hash, far_lat, far_lon, "2026-10-24T12:00:00Z", today_str, code)
    tag = compute_proof_tag(nonce, canonical)

    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": far_lat,
        "lon": far_lon,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": code,
        "tag": tag,
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "E_GPS_FAR"


# 8. NA location with coords job gives gps required
def test_na_location_with_coords_job_gives_gps_required():
    booking_id, worker_id, w_tok, c_tok, _ = setup_in_progress_job(service_lat=28.61234, service_lon=77.20987)
    code = client.get(f"/api/bookings/{booking_id}/completion-code", headers=auth_header(c_tok)).json()["code"]
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, today_str)

    photo_hash = "33334444555566667777888899990000aaaabbbbccccddddeeeeffff11113333"
    canonical = build_canonical(booking_id, worker_id, photo_hash, None, None, "2026-10-24T12:00:00Z", today_str, code)
    tag = compute_proof_tag(nonce, canonical)

    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": None,
        "lon": None,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": code,
        "tag": tag,
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "E_GPS_REQUIRED"


# 9. Wrong code gives code wrong
def test_wrong_code_gives_code_wrong():
    booking_id, worker_id, w_tok, _, _ = setup_in_progress_job()
    wrong_code = "000000"
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, today_str)

    photo_hash = "4444555566667777888899990000aaaabbbbccccddddeeeeffff111122224444"
    canonical = build_canonical(booking_id, worker_id, photo_hash, 28.61, 77.20, "2026-10-24T12:00:00Z", today_str, wrong_code)
    tag = compute_proof_tag(nonce, canonical)

    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": 28.61,
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": wrong_code,
        "tag": tag,
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "E_CODE_WRONG"


# 10. Sixth wrong code gives code locked
def test_sixth_wrong_code_gives_code_locked():
    booking_id, worker_id, w_tok, _, _ = setup_in_progress_job()
    wrong_code = "999999"
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, today_str)

    photo_hash = "555566667777888899990000aaaabbbbccccddddeeeeffff1111222233335555"
    canonical = build_canonical(booking_id, worker_id, photo_hash, 28.61, 77.20, "2026-10-24T12:00:00Z", today_str, wrong_code)
    tag = compute_proof_tag(nonce, canonical)

    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": 28.61,
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": today_str,
        "customer_code": wrong_code,
        "tag": tag,
    }

    # Submit 5 wrong codes
    for _ in range(5):
        res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
        assert res.status_code == 400
        assert res.json()["detail"]["code"] == "E_CODE_WRONG"

    # 6th attempt should be locked
    res6 = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res6.status_code == 400
    assert res6.json()["detail"]["code"] == "E_CODE_LOCKED"


# 11. Stale nonce date gives nonce date
def test_stale_nonce_date_gives_nonce_date():
    booking_id, worker_id, w_tok, c_tok, _ = setup_in_progress_job()
    code = client.get(f"/api/bookings/{booking_id}/completion-code", headers=auth_header(c_tok)).json()["code"]
    stale_date = (datetime.now(IST).date() - timedelta(days=3)).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, stale_date)

    photo_hash = "66667777888899990000aaaabbbbccccddddeeeeffff11112222333344446666"
    canonical = build_canonical(booking_id, worker_id, photo_hash, 28.61, 77.20, "2026-10-24T12:00:00Z", stale_date, code)
    tag = compute_proof_tag(nonce, canonical)

    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": 28.61,
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": stale_date,
        "customer_code": code,
        "tag": tag,
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "E_NONCE_DATE"


# 12. Two day old nonce accepted
def test_two_day_old_nonce_accepted():
    booking_id, worker_id, w_tok, c_tok, _ = setup_in_progress_job()
    code = client.get(f"/api/bookings/{booking_id}/completion-code", headers=auth_header(c_tok)).json()["code"]
    two_day_date = (datetime.now(IST).date() - timedelta(days=2)).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, two_day_date)

    photo_hash = "7777888899990000aaaabbbbccccddddeeeeffff111122223333444455557777"
    canonical = build_canonical(booking_id, worker_id, photo_hash, 28.61, 77.20, "2026-10-24T12:00:00Z", two_day_date, code)
    tag = compute_proof_tag(nonce, canonical)

    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": 28.61,
        "lon": 77.20,
        "captured_at": "2026-10-24T12:00:00Z",
        "nonce_date": two_day_date,
        "customer_code": code,
        "tag": tag,
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res.status_code == 200
    assert res.json()["status"] == "COMPLETED"


# 13. Wrong worker gives state
def test_wrong_worker_gives_state():
    booking_id, _, _, _, _ = setup_in_progress_job()
    db = TestingSessionLocal()
    u2, _ = create_test_worker(db, f"w_wrong_{uuid.uuid4().hex[:6]}", coop_id=1)
    w2_email = u2.email
    db.close()
    w_tok2 = login_token(w2_email)

    res = client.patch(f"/api/bookings/{booking_id}/complete", json={}, headers=auth_header(w_tok2))
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "E_STATE"


# 14. Skip state still rejected
def test_skip_state_still_rejected():
    db = TestingSessionLocal()
    uid = uuid.uuid4().hex[:8]
    admin = User(name=f"Admin {uid}", email=f"admin_{uid}@test.com", password_hash=hash_password("Password123"), role=UserRole.ADMIN)
    db.add(admin)
    db.commit()
    coop = Cooperative(name=f"Coop {uid}", location="Noida", admin_id=admin.id)
    db.add(coop)
    db.commit()
    srv = Service(name=f"Service {uid}", category="Electrical", description="Test srv")
    db.add(srv)
    db.commit()
    cust = User(name=f"Cust {uid}", email=f"cust_{uid}@test.com", password_hash=hash_password("Password123"), role=UserRole.CUSTOMER)
    db.add(cust)
    db.commit()
    w_user, worker = create_test_worker(db, f"w_{uid}", coop.id)
    req = ServiceRequest(
        customer_id=cust.id,
        service_id=srv.id,
        cooperative_id=coop.id,
        description="Fix issue",
        location="Sector 62, Noida",
        preferred_date="2026-10-24",
        preferred_time="10:00",
        status=RequestStatus.PENDING,
    )
    db.add(req)
    db.commit()

    req_id, worker_id, w_email, a_email = req.id, worker.id, w_user.email, admin.email
    db.close()

    a_tok = login_token(a_email)
    w_tok = login_token(w_email)

    alloc_res = client.post(f"/api/requests/{req_id}/allocate", json={"worker_id": worker_id}, headers=auth_header(a_tok)).json()
    booking_id = alloc_res["id"]

    # Try to complete immediately from ASSIGNED
    res = client.patch(f"/api/bookings/{booking_id}/complete", json={}, headers=auth_header(w_tok))
    assert res.status_code == 400
    assert "Cannot transition" in str(res.json()["detail"])


# 15. Valid bundle completes job
def test_valid_bundle_completes_job():
    booking_id, worker_id, w_tok, c_tok, req_id = setup_in_progress_job()
    code = client.get(f"/api/bookings/{booking_id}/completion-code", headers=auth_header(c_tok)).json()["code"]
    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    nonce = get_daily_nonce(worker_id, today_str)

    photo_hash = "888899990000aaaabbbbccccddddeeeeffff1111222233334444555566668888"
    lat, lon = 28.61234, 77.20987
    captured_at = "2026-10-24T12:34:56Z"
    canonical = build_canonical(booking_id, worker_id, photo_hash, lat, lon, captured_at, today_str, code)
    tag = compute_proof_tag(nonce, canonical)

    payload = {
        "proof_of_work_hash": photo_hash,
        "lat": lat,
        "lon": lon,
        "captured_at": captured_at,
        "nonce_date": today_str,
        "customer_code": code,
        "tag": tag,
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=payload, headers=auth_header(w_tok))
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"

    # Verify database fields stored
    db = TestingSessionLocal()
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    assert b.status == BookingStatus.COMPLETED
    assert b.proof_tag == tag
    assert b.proof_of_work_hash == photo_hash
    assert abs(b.proof_lat - lat) < 1e-4
    assert abs(b.proof_lon - lon) < 1e-4
    assert b.proof_captured_at is not None

    # Verify worker total_jobs incremented
    w = db.query(Worker).filter(Worker.id == worker_id).first()
    assert w.total_jobs == 1
    db.close()
