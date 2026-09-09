"""
Cooperative business logic layer.

Manages cooperative initialization, retrieval, and live database statistics calculation.
"""
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.cooperative import Cooperative
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.schemas.cooperative import CooperativeStatsResponse

DEFAULT_COOP_NAME = "Ghaziabad Community Services Cooperative"
DEFAULT_COOP_LOCATION = "Ghaziabad, Uttar Pradesh"
DEFAULT_COOP_DESC = "Worker-owned household and community services cooperative"


def get_demo_cooperative(db: Session) -> Optional[Cooperative]:
    """Return the primary cooperative or None."""
    return db.query(Cooperative).first()


def ensure_demo_cooperative(db: Session, admin_id: Optional[int] = None) -> Cooperative:
    """
    Ensure the primary demo cooperative exists in the database.
    Creates it if absent and links the admin_id.
    """
    coop = get_demo_cooperative(db)
    if coop:
        if admin_id and coop.admin_id != admin_id:
            coop.admin_id = admin_id
            db.commit()
            db.refresh(coop)
        return coop

    coop = Cooperative(
        name=DEFAULT_COOP_NAME,
        location=DEFAULT_COOP_LOCATION,
        description=DEFAULT_COOP_DESC,
        admin_id=admin_id,
    )
    db.add(coop)
    db.commit()
    db.refresh(coop)
    return coop


def get_cooperative_stats(db: Session) -> CooperativeStatsResponse:
    """
    Calculate live workforce and verification statistics directly from the database.
    """
    total = db.query(func.count(Worker.id)).scalar() or 0
    verified = db.query(func.count(Worker.id)).filter(Worker.verification_status == VerificationStatus.VERIFIED).scalar() or 0
    pending = db.query(func.count(Worker.id)).filter(Worker.verification_status == VerificationStatus.PENDING).scalar() or 0
    rejected = db.query(func.count(Worker.id)).filter(Worker.verification_status == VerificationStatus.REJECTED).scalar() or 0
    available = db.query(func.count(Worker.id)).filter(Worker.availability == AvailabilityStatus.AVAILABLE).scalar() or 0
    unavailable = db.query(func.count(Worker.id)).filter(Worker.availability == AvailabilityStatus.UNAVAILABLE).scalar() or 0

    return CooperativeStatsResponse(
        total_workers=total,
        verified_workers=verified,
        pending_workers=pending,
        rejected_workers=rejected,
        available_workers=available,
        unavailable_workers=unavailable,
    )

from app.models.booking import Booking
from app.models.service_request import ServiceRequest
from app.models.service import Service
from app.schemas.cooperative import AnalyticsResponse
from collections import defaultdict
from datetime import datetime, timedelta

def get_cooperative_analytics(db: Session) -> AnalyticsResponse:
    # Status breakdown
    all_bookings = db.query(Booking).all()
    status_counts = defaultdict(int)
    for b in all_bookings:
        status_counts[b.status.value] += 1
        
    # Category breakdown
    category_counts = defaultdict(int)
    requests = db.query(ServiceRequest).all()
    for req in requests:
        svc = db.query(Service).filter(Service.id == req.service_id).first()
        if svc:
            category_counts[svc.category] += 1
            
    # Trend (last 7 days of completed jobs)
    trend = []
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        count = db.query(func.count(Booking.id))\
            .filter(Booking.status == 'COMPLETED')\
            .filter(func.date(Booking.updated_at) == str(d))\
            .scalar()
        trend.append({"date": str(d), "count": count or 0})
        
    return AnalyticsResponse(
        jobs_by_status=dict(status_counts),
        jobs_by_category=dict(category_counts),
        recent_jobs_trend=trend
    )
