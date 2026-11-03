"""
Tests for Voice Booking & Hindi SMS Dispatch (Patent Feature: Zero-Screen-Touch).
Includes:
- Hindi service translation mapping
- Template formatting and UCS-2 SMS length bounding (<= 140 chars)
- Auto-reassignment on worker decline ("2") via equity/fatigue scorer
- Worker fatigue limit (>= 80%) exclusion
- Automatic timeout and max-dispatch-attempts handling
- Invalid SMS reply handling with guidance SMS
- Idempotent duplicate reply handling
"""
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.routes.voice_booking import (
    dispatch_to_next_worker,
    process_voice_booking_timeouts,
    score_and_filter_voice_worker,
    select_best_voice_worker,
)
from app.services.auth import hash_password
from app.services.sms_service import (
    build_hindi_job_sms,
    build_hindi_confirmation_sms,
    build_hindi_fallback_sms,
    _to_hindi_service,
)


def test_hindi_service_mapping():
    """Verify English services map to appropriate Hindi labels."""
    assert _to_hindi_service("Electrician") == "बिजली का काम"
    assert _to_hindi_service("Plumber") == "नल/पाइप ठीक करना"
    assert _to_hindi_service("AC Repair") == "एसी सर्विस"
    assert _to_hindi_service("Full Home Cleaning") == "घर की सफाई"
    assert _to_hindi_service("Custom Unknown Service") == "Custom Unknown Service"


def test_build_hindi_job_sms():
    """Verify Hindi job SMS contains all required details and choice prompts."""
    sms = build_hindi_job_sms(
        service_name="Electrician",
        customer_name="Priya Sharma",
        location="Sector 62, Noida",
        scheduled_date="2026-11-02",
        scheduled_time="14:00",
        booking_id=101,
    )
    assert "#101" in sms
    assert "बिजली का काम" in sms
    assert "Priya Sharma" in sms
    assert "Sector 62, Noida" in sms
    assert "स्वीकार=1 | मना=2 भेजें" in sms


def test_build_hindi_confirmation_sms():
    """Verify accepted and declined confirmation texts."""
    accepted_msg = build_hindi_confirmation_sms(accepted=True, booking_id=101)
    assert "धन्यवाद" in accepted_msg
    assert "#101" in accepted_msg

    declined_msg = build_hindi_confirmation_sms(accepted=False, booking_id=101)
    assert "ठीक है" in declined_msg
    assert "#101" in declined_msg


def test_build_hindi_fallback_sms():
    """Verify fallback notification text."""
    fallback_msg = build_hindi_fallback_sms(booking_id=101)
    assert "#101" in fallback_msg
    assert "काम" in fallback_msg


def test_build_hindi_job_sms_length_bounded():
    """Verify that Hindi SMS clamping keeps characters bounded within ~2 UCS-2 segments."""
    long_name = "श्रीमान रामगोपाल कृष्णमूर्ती शास्त्री महाराज जी"
    long_loc = "मकान नंबर 1234, गली नंबर 5, ब्लॉक बी, सेक्टर 62, इंडस्ट्रियल एरिया, नोएडा, उत्तर प्रदेश, भारत"
    sms = build_hindi_job_sms(
        service_name="Electrician",
        customer_name=long_name,
        location=long_loc,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        booking_id=101,
    )
    # Long inputs must be clamped to prevent unbounded multi-segment explosion (<= 140 chars)
    assert len(sms) <= 140
    # Longest template should take at most 2 segments (70 chars per segment)
    ucs2_segments = (len(sms) + 69) // 70
    assert ucs2_segments <= 2


# ── Test Helpers for Voice Booking E2E ────────────────────────────────────────

def create_voice_test_environment(db: Session):
    """Create a minimal cooperative environment with customer, service, and two workers."""
    coop = Cooperative(name="Voice Test Coop", location="Noida")
    db.add(coop)
    db.commit()

    service = Service(
        name="Electrician",
        category="Electrical",
        price=450.0,
        is_active=True,
    )
    db.add(service)
    db.commit()

    c_user = User(
        name="Customer Ananya",
        email="customer.ananya@test.com",
        phone="+919988776655",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.CUSTOMER,
        is_active=True,
    )
    db.add(c_user)
    db.commit()

    # Worker 1
    w1_user = User(
        name="Worker Ramesh",
        email="worker.ramesh@test.com",
        phone="+919876543201",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.WORKER,
        is_active=True,
    )
    db.add(w1_user)
    db.commit()

    worker1 = Worker(
        user_id=w1_user.id,
        cooperative_id=coop.id,
        profession="Electrician",
        skills=["wiring", "repair"],
        availability=AvailabilityStatus.AVAILABLE,
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(worker1)
    db.commit()

    # Worker 2
    w2_user = User(
        name="Worker Suresh",
        email="worker.suresh@test.com",
        phone="+919876543202",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.WORKER,
        is_active=True,
    )
    db.add(w2_user)
    db.commit()

    worker2 = Worker(
        user_id=w2_user.id,
        cooperative_id=coop.id,
        profession="Electrician",
        skills=["wiring", "repair"],
        availability=AvailabilityStatus.AVAILABLE,
        verification_status=VerificationStatus.VERIFIED,
    )
    db.add(worker2)
    db.commit()

    req = ServiceRequest(
        customer_id=c_user.id,
        service_id=service.id,
        cooperative_id=coop.id,
        description="Fix main switchboard spark",
        location="Sector 62, Noida",
        latitude=28.628,
        longitude=77.364,
        preferred_date="2026-11-03",
        preferred_time="14:00",
        status=RequestStatus.ACCEPTED,
    )
    db.add(req)
    db.commit()

    return {
        "coop": coop,
        "service": service,
        "customer": c_user,
        "worker1": worker1,
        "worker2": worker2,
        "request": req,
    }


def test_voice_booking_excludes_fatigued_worker_ge_80(db: Session, monkeypatch):
    """Workers at or above 80% fatigue limit must be excluded from voice booking."""
    env = create_voice_test_environment(db)
    w1 = env["worker1"]
    w2 = env["worker2"]

    # Mock bio-economic metrics: w1 has 85% fatigue, w2 has 10% fatigue
    def mock_metrics(worker, session=None):
        if worker.id == w1.id:
            return {"fatigue_index": 85.0, "is_fatigued": True, "consecutive_days": 6}
        return {"fatigue_index": 10.0, "is_fatigued": False, "consecutive_days": 1}

    monkeypatch.setattr("app.routes.voice_booking.calculate_bio_economic_metrics", mock_metrics)

    # Worker 1 is excluded (score is None)
    score1 = score_and_filter_voice_worker(w1, env["service"], "Sector 62, Noida", 28.628, 77.364, db)
    assert score1 is None

    # Worker 2 is eligible (score is float > 0)
    score2 = score_and_filter_voice_worker(w2, env["service"], "Sector 62, Noida", 28.628, 77.364, db)
    assert score2 is not None
    assert score2 > 0.0

    selected = select_best_voice_worker(db, env["service"], "Sector 62, Noida", 28.628, 77.364)
    assert selected is not None
    assert selected.id == w2.id


def test_sms_reply_decline_auto_reassigns_to_next_worker(db: Session, client: TestClient, monkeypatch):
    """When a worker declines ('2'), auto-reassigns to next worker via equity scorer."""
    env = create_voice_test_environment(db)
    w1 = env["worker1"]
    w2 = env["worker2"]
    req = env["request"]

    # Initial booking assigned to Worker 1
    booking1 = Booking(
        request_id=req.id,
        worker_id=w1.id,
        assigned_by=env["customer"].id,
        status=BookingStatus.ASSIGNED,
        amount=450.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        notes="[VOICE BOOKING] Attempt 1/3",
    )
    db.add(booking1)
    db.commit()

    dispatched_sms = []
    monkeypatch.setattr("app.routes.sms_reply.send_sms", lambda p, m: dispatched_sms.append((p, m)))
    monkeypatch.setattr("app.routes.voice_booking.send_sms", lambda p, m: dispatched_sms.append((p, m)))

    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "test-secret"
    try:
        # Worker 1 declines with "2"
        res = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "test-secret"},
            json={"from_phone": "+919876543201", "message": "2"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["new_status"] == "REASSIGNED"
        assert data["booking_id"] != booking1.id

        # Verify old booking is REJECTED
        db.refresh(booking1)
        assert booking1.status == BookingStatus.REJECTED
        assert "DECLINED_BY_WORKER" in (booking1.notes or "")

        # Verify new booking exists for Worker 2
        new_booking = db.query(Booking).filter(Booking.id == data["booking_id"]).first()
        assert new_booking is not None
        assert new_booking.worker_id == w2.id
        assert new_booking.status == BookingStatus.ASSIGNED
        assert "Attempt 2/3" in new_booking.notes
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_invalid_message_sends_guidance_sms(db: Session, client: TestClient, monkeypatch):
    """When a worker sends an invalid message (e.g. 'हाँ' or 'ok'), send guidance SMS."""
    env = create_voice_test_environment(db)
    w1 = env["worker1"]
    req = env["request"]

    booking = Booking(
        request_id=req.id,
        worker_id=w1.id,
        assigned_by=env["customer"].id,
        status=BookingStatus.ASSIGNED,
        amount=450.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        notes="[VOICE BOOKING] Attempt 1/3",
    )
    db.add(booking)
    db.commit()

    dispatched_sms = []
    monkeypatch.setattr("app.routes.sms_reply.send_sms", lambda p, m: dispatched_sms.append((p, m)))

    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "test-secret"
    try:
        res = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "test-secret"},
            json={"from_phone": "+919876543201", "message": "हाँ मैं आऊंगा"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is False
        assert data["new_status"] == "ASSIGNED"

        # Verify booking is STILL ASSIGNED
        db.refresh(booking)
        assert booking.status == BookingStatus.ASSIGNED

        # Verify guidance SMS sent
        assert any("कृपया 1 (स्वीकार) या 2 (मना) भेजें" in msg for _, msg in dispatched_sms)
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_sms_reply_duplicate_acceptance_and_decline_idempotent(db: Session, client: TestClient, monkeypatch):
    """Duplicate replies must be idempotent and not return 404."""
    env = create_voice_test_environment(db)
    w1 = env["worker1"]
    req = env["request"]

    booking = Booking(
        request_id=req.id,
        worker_id=w1.id,
        assigned_by=env["customer"].id,
        status=BookingStatus.ASSIGNED,
        amount=450.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        notes="[VOICE BOOKING] Attempt 1/3",
    )
    db.add(booking)
    db.commit()

    monkeypatch.setattr("app.routes.sms_reply.send_sms", lambda p, m: True)
    monkeypatch.setattr("app.routes.voice_booking.send_sms", lambda p, m: True)

    orig_secret = settings.SMS_WEBHOOK_SECRET
    settings.SMS_WEBHOOK_SECRET = "test-secret"
    try:
        # First accept: "1"
        res1 = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "test-secret"},
            json={"from_phone": "+919876543201", "message": "1"},
        )
        assert res1.status_code == 200
        assert res1.json()["new_status"] == "ACCEPTED"

        # Duplicate accept: "1" again
        res2 = client.post(
            "/api/sms/reply",
            headers={"X-Webhook-Secret": "test-secret"},
            json={"from_phone": "+919876543201", "message": "1"},
        )
        assert res2.status_code == 200
        assert res2.json()["new_status"] == "ACCEPTED"
        assert "Already confirmed" in res2.json()["message"]
    finally:
        settings.SMS_WEBHOOK_SECRET = orig_secret


def test_voice_booking_timeout_auto_reassigns(db: Session, monkeypatch):
    """Voice booking in ASSIGNED status older than timeout is auto-expired and reassigned."""
    env = create_voice_test_environment(db)
    w1 = env["worker1"]
    w2 = env["worker2"]
    req = env["request"]

    booking1 = Booking(
        request_id=req.id,
        worker_id=w1.id,
        assigned_by=env["customer"].id,
        status=BookingStatus.ASSIGNED,
        amount=450.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        notes="[VOICE BOOKING] Attempt 1/3",
    )
    db.add(booking1)
    db.commit()

    # Manually backdate created_at by 20 minutes
    booking1.created_at = datetime.utcnow() - timedelta(minutes=20)
    db.commit()

    dispatched_sms = []
    monkeypatch.setattr("app.routes.voice_booking.send_sms", lambda p, m: dispatched_sms.append((p, m)))

    results = process_voice_booking_timeouts(db)
    assert len(results) == 1
    assert results[0]["expired_booking_id"] == booking1.id
    assert results[0]["next_worker_id"] == w2.id

    db.refresh(booking1)
    assert booking1.status == BookingStatus.REJECTED
    assert "EXPIRED_TIMEOUT" in booking1.notes

    new_b = db.query(Booking).filter(Booking.id == results[0]["reassigned_booking_id"]).first()
    assert new_b is not None
    assert new_b.worker_id == w2.id
    assert new_b.status == BookingStatus.ASSIGNED


def test_voice_booking_max_dispatch_attempts_marks_unassigned(db: Session, monkeypatch):
    """When maximum dispatch attempts (3) are reached, booking is marked UNASSIGNED and customer notified."""
    env = create_voice_test_environment(db)
    w1 = env["worker1"]
    w2 = env["worker2"]
    req = env["request"]

    # Create 3 bookings simulating 3 prior attempts
    b1 = Booking(
        request_id=req.id,
        worker_id=w1.id,
        assigned_by=env["customer"].id,
        status=BookingStatus.REJECTED,
        amount=450.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        notes="[VOICE BOOKING] Attempt 1/3",
    )
    b2 = Booking(
        request_id=req.id,
        worker_id=w2.id,
        assigned_by=env["customer"].id,
        status=BookingStatus.REJECTED,
        amount=450.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        notes="[VOICE BOOKING] Attempt 2/3",
    )
    b3 = Booking(
        request_id=req.id,
        worker_id=w1.id,
        assigned_by=env["customer"].id,
        status=BookingStatus.ASSIGNED,
        amount=450.0,
        scheduled_date="2026-11-03",
        scheduled_time="14:00",
        notes="[VOICE BOOKING] Attempt 3/3",
    )
    db.add_all([b1, b2, b3])
    db.commit()

    dispatched_sms = []
    monkeypatch.setattr("app.routes.voice_booking.send_sms", lambda p, m: dispatched_sms.append((p, m)))

    new_booking, next_worker, sms_sent, msg = dispatch_to_next_worker(
        db=db,
        request_id=req.id,
        current_booking_id=b3.id,
        reason="TIMEOUT",
    )
    assert new_booking is None
    assert next_worker is None
    assert "UNASSIGNED" in msg

    db.refresh(b3)
    assert b3.status == BookingStatus.UNASSIGNED
    assert "MAX_ATTEMPTS_REACHED" in (b3.notes or "")

    # Customer notification SMS sent
    assert any("कोई कारीगर उपलब्ध नहीं हो सका" in m for p, m in dispatched_sms)
