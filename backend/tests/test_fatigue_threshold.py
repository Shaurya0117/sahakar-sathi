from datetime import datetime, timezone
import pytest

from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.booking import Booking, BookingStatus
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.matching.engine import get_matching_recommendations
from app.services.matching.scorer import calculate_bio_economic_metrics
from app.config import MAX_FATIGUE_THRESHOLD
from tests.conftest import TestingSessionLocal


def setup_base_environment(db):
    admin = User(name="Admin User", email="admin_fatigue@test.com", password_hash="hash", role=UserRole.ADMIN)
    db.add(admin)
    db.commit()

    coop = Cooperative(name="Fatigue Test Coop", location="Noida", admin_id=admin.id)
    db.add(coop)
    db.commit()

    customer = User(name="Customer User", email="cust_fatigue@test.com", password_hash="hash", role=UserRole.CUSTOMER)
    db.add(customer)
    db.commit()

    worker_user = User(name="Worker User", email="worker_fatigue@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(worker_user)
    db.commit()

    worker = Worker(
        user_id=worker_user.id,
        cooperative_id=coop.id,
        profession="General Technician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["General Maintenance", "Repairs"],
        rating=4.5,
        experience_years=3,
        location="Sector 62, Noida",
    )
    db.add(worker)
    db.commit()

    # The new service request to match
    match_service = Service(
        name="General Maintenance Service",
        category="general",
        description="Standard maintenance job",
        duration_minutes=60,
    )
    db.add(match_service)
    db.commit()

    new_request = ServiceRequest(
        customer_id=customer.id,
        service_id=match_service.id,
        cooperative_id=coop.id,
        description="Routine maintenance required",
        location="Sector 62, Noida",
        preferred_date="2026-08-30",
        preferred_time="10:00",
        status=RequestStatus.PENDING,
    )
    db.add(new_request)
    db.commit()

    return admin, coop, customer, worker, match_service, new_request


def test_fatigued_worker_excluded():
    """Create a booking scenario where a worker's fatigue_index is 85 (above 80) and verify the matching engine skips them."""
    db = TestingSessionLocal()
    try:
        admin, coop, customer, worker, match_service, new_request = setup_base_environment(db)

        # Service for past completed booking: intensity = 0.50, duration = 1836 minutes (30.6 hours)
        # load = 0.50 * 30.6 = 15.3; safe_load = 18.0; fatigue_index = (15.3 / 18.0) * 100 = 85.0
        heavy_service = Service(
            name="General Maintenance Overhaul",
            category="general",
            duration_minutes=1836,
        )
        db.add(heavy_service)
        db.commit()

        past_req = ServiceRequest(
            customer_id=customer.id,
            service_id=heavy_service.id,
            cooperative_id=coop.id,
            description="Heavy overhaul work",
            location="Sector 62, Noida",
            preferred_date="2026-08-29",
            preferred_time="09:00",
            status=RequestStatus.COMPLETED,
        )
        db.add(past_req)
        db.commit()

        now = datetime.now(timezone.utc)
        completed_booking = Booking(
            request_id=past_req.id,
            worker_id=worker.id,
            assigned_by=admin.id,
            status=BookingStatus.COMPLETED,
            amount=2000.0,
            scheduled_date="2026-08-29",
            scheduled_time="09:00",
            updated_at=now,
            created_at=now,
        )
        db.add(completed_booking)
        db.commit()

        # Check bio-economic metrics directly
        bio_metrics = calculate_bio_economic_metrics(worker, db)
        assert bio_metrics["fatigue_index"] == 85.0
        assert bio_metrics["fatigue_index"] > MAX_FATIGUE_THRESHOLD
        assert bio_metrics["is_fatigued"] is True

        # Verify matching engine skips them
        response = get_matching_recommendations(db, new_request.id)
        recommended_worker_ids = [r.worker_id for r in response.recommendations]
        assert worker.id not in recommended_worker_ids
        assert response.candidate_count == 0
    finally:
        db.close()


def test_non_fatigued_worker_included():
    """Create a booking scenario where fatigue_index = 75 (below 80) and verify included."""
    db = TestingSessionLocal()
    try:
        admin, coop, customer, worker, match_service, new_request = setup_base_environment(db)

        # Service for past completed booking: intensity = 0.50, duration = 1620 minutes (27.0 hours)
        # load = 0.50 * 27.0 = 13.5; safe_load = 18.0; fatigue_index = (13.5 / 18.0) * 100 = 75.0
        moderate_service = Service(
            name="General Maintenance Routine",
            category="general",
            duration_minutes=1620,
        )
        db.add(moderate_service)
        db.commit()

        past_req = ServiceRequest(
            customer_id=customer.id,
            service_id=moderate_service.id,
            cooperative_id=coop.id,
            description="Routine service work",
            location="Sector 62, Noida",
            preferred_date="2026-08-29",
            preferred_time="09:00",
            status=RequestStatus.COMPLETED,
        )
        db.add(past_req)
        db.commit()

        now = datetime.now(timezone.utc)
        completed_booking = Booking(
            request_id=past_req.id,
            worker_id=worker.id,
            assigned_by=admin.id,
            status=BookingStatus.COMPLETED,
            amount=2000.0,
            scheduled_date="2026-08-29",
            scheduled_time="09:00",
            updated_at=now,
            created_at=now,
        )
        db.add(completed_booking)
        db.commit()

        # Check bio-economic metrics directly
        bio_metrics = calculate_bio_economic_metrics(worker, db)
        assert bio_metrics["fatigue_index"] == 75.0
        assert bio_metrics["fatigue_index"] < MAX_FATIGUE_THRESHOLD
        assert bio_metrics["is_fatigued"] is False

        # Verify matching engine includes them
        response = get_matching_recommendations(db, new_request.id)
        recommended_worker_ids = [r.worker_id for r in response.recommendations]
        assert worker.id in recommended_worker_ids
        assert response.candidate_count == 1
    finally:
        db.close()
