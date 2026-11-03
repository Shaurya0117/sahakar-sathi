"""
Security Hardening Tests for Sahakar Sathi.

Verifies:
1. SMS Webhook Auth: header matching, rejection on missing/wrong secret, production behavior.
2. Timestamp validation and active booking checks on SMS reply webhook.
3. Simulate reply disabled in production.
4. Public test endpoints (/api/channels/voice/test-input & whatsapp/test-message) return 404 in production.
5. /api/ml/bandit/reset is POST only (GET returns 405).
6. Production startup validation fails with default/missing SECRET_KEY or PROOF_SECRET.
7. Sliding-window rate limiting returns 429 when threshold exceeded.
"""
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.rate_limiter import reset_rate_limits
from app.config import settings
from app.main import app, check_production_secrets
from app.models.booking import Booking, BookingStatus
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.auth import hash_password


@pytest.fixture(autouse=True)
def clean_rate_limits(monkeypatch):
    """Ensure rate limits are clean before and after each test and mock external SMS."""
    monkeypatch.setattr("app.routes.sms_reply.send_sms", lambda phone, msg: True)
    reset_rate_limits()
    yield
    reset_rate_limits()


def setup_worker_with_booking(db: Session, phone: str = "+919876543210", suffix: str = ""):
    """Helper to create a coop, worker, customer, request, and ASSIGNED booking."""
    coop = Cooperative(name=f"Security Test Coop{suffix}", location="Noida")
    db.add(coop)
    db.commit()

    service = Service(name=f"Electrical Repair Test{suffix}", category="Electrical", price=500.0, is_active=True)
    db.add(service)
    db.commit()

    w_user = User(
        name=f"Security Worker{suffix}",
        email=f"sec.worker{suffix}@test.com",
        phone=phone,
        password_hash=hash_password("Worker@1234"),
        role=UserRole.WORKER,
        is_active=True,
    )
    db.add(w_user)
    db.commit()

    worker = Worker(
        user_id=w_user.id,
        cooperative_id=coop.id,
        profession="Electrician",
        skills=["wiring"],
        availability=AvailabilityStatus.AVAILABLE,
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(worker)
    db.commit()

    c_user = User(
        name=f"Security Customer{suffix}",
        email=f"sec.customer{suffix}@test.com",
        phone=f"+91987659{suffix.zfill(4)}" if suffix else "+919876599999",
        password_hash=hash_password("Customer@1234"),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db.add(c_user)
    db.commit()

    req = ServiceRequest(
        customer_id=c_user.id,
        service_id=service.id,
        cooperative_id=coop.id,
        description="Fix switch",
        location="Sector 62, Noida",
        preferred_date="2026-11-03",
        preferred_time="14:00",
        status=RequestStatus.ACCEPTED,
    )
    db.add(req)
    db.commit()

    booking = Booking(
        request_id=req.id,
        worker_id=worker.id,
        assigned_by=c_user.id,
        status=BookingStatus.ASSIGNED,
        amount=500.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return booking, worker, c_user


# ── 1. SMS Reply Webhook Authentication ───────────────────────────────────────

def test_sms_reply_without_secret_returns_401(client: TestClient, db: Session):
    booking, worker, _ = setup_worker_with_booking(db)
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        res = client.post(
            "/api/sms/reply",
            json={"from_phone": "+919876543210", "message": "1"},
        )
        assert res.status_code == 401
        assert "X-Webhook-Secret" in res.json().get("detail", "")
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_with_wrong_secret_returns_401(client: TestClient, db: Session):
    booking, worker, _ = setup_worker_with_booking(db)
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        # Wrong header secret
        res = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "wrong-secret"},
            json={"from_phone": "+919876543210", "message": "1"},
        )
        assert res.status_code == 401
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_with_wrong_query_secret_returns_401(client: TestClient, db: Session):
    booking, worker, _ = setup_worker_with_booking(db)
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        # Wrong query parameter secret
        res = client.post(
            "/api/sms/reply?secret=wrong-query-secret",
            json={"from_phone": "+919876543210", "message": "1"},
        )
        assert res.status_code == 401
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_with_correct_secret_header_works(client: TestClient, db: Session):
    booking, worker, _ = setup_worker_with_booking(db)
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        res = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "super-secret-webhook-key"},
            json={"from_phone": "+919876543210", "message": "1"},
        )
        assert res.status_code == 200
        assert res.json()["new_status"] == "ACCEPTED"
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_with_correct_query_param_works(client: TestClient, db: Session):
    booking, worker, _ = setup_worker_with_booking(db)
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        res = client.post(
            "/api/sms/reply?secret=super-secret-webhook-key",
            json={"from_phone": "+919876543210", "message": "1"},
        )
        assert res.status_code == 200
        assert res.json()["new_status"] == "ACCEPTED"
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_older_than_24h_rejected(client: TestClient, db: Session):
    booking, worker, _ = setup_worker_with_booking(db)
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        res = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "super-secret-webhook-key"},
            json={"from_phone": "+919876543210", "message": "1", "timestamp": old_time},
        )
        assert res.status_code == 400
        assert "24 hours" in res.json().get("detail", "")
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_unknown_phone_ignored(client: TestClient, db: Session):
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        res = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "super-secret-webhook-key"},
            json={"from_phone": "+910000000000", "message": "1"},
        )
        assert res.status_code == 404
        assert "no worker found" in res.json().get("detail", "").lower()
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_simulate_reply_disabled_in_production(client: TestClient, db: Session):
    booking, worker, c_user = setup_worker_with_booking(db)
    orig_env = settings.APP_ENV
    settings.APP_ENV = "production"

    try:
        # Login as customer to get token
        login_res = client.post("/api/auth/login", data={"username": "sec.customer@test.com", "password": "Customer@1234"})
        token = login_res.json()["access_token"]

        res = client.post(
            "/api/sms/simulate-reply",
            headers={"Authorization": f"Bearer {token}"},
            json={"booking_id": booking.id, "reply": "1"},
        )
        assert res.status_code == 403
        assert "disabled in production" in res.json().get("detail", "")
    finally:
        settings.APP_ENV = orig_env


# ── 2. Public Test Endpoints Disabled in Production ───────────────────────────

def test_public_test_endpoints_return_404_when_production(client: TestClient):
    orig_env = settings.APP_ENV
    settings.APP_ENV = "production"

    try:
        # Voice test input
        v_res = client.post("/api/channels/voice/test-input", json={"phone": "+919876500000"})
        assert v_res.status_code == 404

        # WhatsApp test message
        w_res = client.post("/api/channels/whatsapp/test-message", json={"phone": "+919876500000", "message": "hello"})
        assert w_res.status_code == 404
    finally:
        settings.APP_ENV = orig_env


# ── 3. State-Changing GET: Bandit Reset is POST Only ──────────────────────────

def test_bandit_reset_is_post_only(client: TestClient, db: Session):
    # Create admin
    admin = User(
        name="Admin Test",
        email="admin.sec@test.com",
        password_hash=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    token_res = client.post("/api/auth/login", data={"username": "admin.sec@test.com", "password": "Admin@1234"})
    token = token_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # GET must return 405 Method Not Allowed
    get_res = client.get("/api/ml/bandit/reset", headers=headers)
    assert get_res.status_code == 405

    # POST must succeed
    post_res = client.post("/api/ml/bandit/reset", headers=headers)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "ok"


# ── 4. Secrets Validation at Startup in Production ────────────────────────────

def test_startup_fails_in_production_with_default_secrets():
    orig_env = settings.APP_ENV
    orig_proof = settings.PROOF_SECRET
    settings.APP_ENV = "production"
    settings.PROOF_SECRET = "dev-change-me-before-deploy"

    try:
        with pytest.raises(RuntimeError, match="PROOF_SECRET must be set"):
            check_production_secrets()
    finally:
        settings.APP_ENV = orig_env
        settings.PROOF_SECRET = orig_proof


def test_startup_fails_in_production_with_default_secret_key():
    orig_env = settings.APP_ENV
    orig_key = settings.SECRET_KEY
    settings.APP_ENV = "production"
    settings.SECRET_KEY = "change-me"

    try:
        with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
            check_production_secrets()
    finally:
        settings.APP_ENV = orig_env
        settings.SECRET_KEY = orig_key


# ── 5. Rate Limiting (Returns 429) ─────────────────────────────────────────────

def test_rate_limit_login_returns_429(client: TestClient, db: Session):
    # Ensure user exists
    user = User(
        name="Rate Limit User",
        email="ratelimit@test.com",
        password_hash=hash_password("Password@1234"),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db.add(user)
    db.commit()

    # 10 requests should pass (or succeed/fail password)
    for i in range(10):
        res = client.post("/api/auth/login", data={"username": "ratelimit@test.com", "password": "Password@1234"})
        assert res.status_code == 200

    # 11th request must trigger 429
    res_11 = client.post("/api/auth/login", data={"username": "ratelimit@test.com", "password": "Password@1234"})
    assert res_11.status_code == 429
    assert "Rate limit exceeded" in res_11.json().get("detail", "")


def test_sms_reply_rate_limit_11_rapid_replies_from_one_phone_returns_429(client: TestClient, db: Session):
    booking, worker, _ = setup_worker_with_booking(db)
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        # First 10 requests from this phone should succeed
        for i in range(10):
            booking.status = BookingStatus.ASSIGNED
            db.commit()
            res = client.post(
                "/api/sms/reply",
                headers={"X-Webhook-Secret": "super-secret-webhook-key"},
                json={"from_phone": "+919876543210", "message": "1"},
            )
            assert res.status_code == 200

        # 11th request from the same phone within 60s must return 429
        res_11 = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "super-secret-webhook-key"},
            json={"from_phone": "+919876543210", "message": "1"},
        )
        assert res_11.status_code == 429
        assert "Rate limit exceeded" in res_11.json().get("detail", "")
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_different_phones_same_ip_not_blocked(client: TestClient, db: Session):
    booking1, worker1, _ = setup_worker_with_booking(db, phone="+919876543210", suffix="1")
    booking2, worker2, _ = setup_worker_with_booking(db, phone="+919876543211", suffix="2")
    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "super-secret-webhook-key"

    try:
        # Phone 1 makes 10 rapid replies
        for i in range(10):
            booking1.status = BookingStatus.ASSIGNED
            db.commit()
            res1 = client.post(
                "/api/sms/reply",
                headers={"X-Webhook-Secret": "super-secret-webhook-key"},
                json={"from_phone": "+919876543210", "message": "1"},
            )
            assert res1.status_code == 200

        # Phone 2 from the exact same client IP is NOT blocked
        res2 = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "super-secret-webhook-key"},
            json={"from_phone": "+919876543211", "message": "1"},
        )
        assert res2.status_code == 200
        assert res2.json()["new_status"] == "ACCEPTED"
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


# ── 6. Bandit State Persistence & Resilience on Fresh Clone ───────────────────

def test_bandit_missing_file_creates_defaults(tmp_path, monkeypatch):
    from app.ml import bandit
    test_path = tmp_path / "artifacts" / "bandit_state.json"
    monkeypatch.setattr(bandit, "BANDIT_STATE_PATH", test_path)
    bandit.reset_state()
    assert not test_path.exists()

    bandit._load_state()
    assert test_path.is_file()
    assert "electrician_morning" in bandit._bandit_state
    assert bandit._bandit_state["electrician_morning"]["alpha"] == [1.0, 1.0, 1.0]
    assert bandit._bandit_state["electrician_morning"]["beta"] == [1.0, 1.0, 1.0]


def test_bandit_corrupted_file_restores_defaults(tmp_path, monkeypatch):
    from app.ml import bandit
    test_dir = tmp_path / "artifacts"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_path = test_dir / "bandit_state.json"
    test_path.write_text("{ this is completely corrupted json !!!", encoding="utf-8")
    monkeypatch.setattr(bandit, "BANDIT_STATE_PATH", test_path)
    bandit.reset_state()

    bandit._load_state()
    assert test_path.is_file()
    assert "plumber_afternoon" in bandit._bandit_state
    assert bandit._bandit_state["plumber_afternoon"]["alpha"] == [1.0, 1.0, 1.0]
    assert bandit._bandit_state["plumber_afternoon"]["beta"] == [1.0, 1.0, 1.0]
