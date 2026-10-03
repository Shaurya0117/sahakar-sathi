import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal
from app.models.user import User, UserRole
from app.models.worker import Worker, VerificationStatus, AvailabilityStatus
from app.models.booking import Booking, BookingStatus
from app.models.service_request import ServiceRequest
from app.services.auth import hash_password
from datetime import datetime

db = SessionLocal()

workers = db.query(Worker).limit(3).all()

req = ServiceRequest(
    customer_id=2, service_id=1, cooperative_id=1,
    description="Test", location="Noida", preferred_date="2026-10-04", preferred_time="10:00:00",
    status="COMPLETED"
)
db.add(req)
db.commit()

for w in workers:
    for _ in range(5):
        b = Booking(
            request_id=req.id, worker_id=w.id, assigned_by=1, status=BookingStatus.COMPLETED,
            amount=500, scheduled_date="2026-10-04", scheduled_time="10:00:00",
            customer_rating=5, arrived_at=datetime.utcnow(), proof_of_work_hash="fakehash"
        )
        db.add(b)
    w.peer_votes = 3
    w.verification_status = VerificationStatus.VERIFIED
    
u = User(name="Pending", email="pending@test.com", password_hash=hash_password("pw"), role=UserRole.WORKER, is_active=True)
db.add(u)
db.commit()

pw = Worker(user_id=u.id, cooperative_id=1, profession="Plumber", availability=AvailabilityStatus.AVAILABLE, verification_status=VerificationStatus.PENDING, peer_votes=0, rating=0.0, total_jobs=0)
db.add(pw)
db.commit()
print("Success")

