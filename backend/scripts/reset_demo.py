import sys
import os
import uuid
import datetime

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import Base, engine, SessionLocal
import scripts.seed_demo_data

client = TestClient(app)

def main():
    print("Dropping DB...")
    Base.metadata.drop_all(bind=engine)
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Seeding demo data...")
    scripts.seed_demo_data.seed_demo_data()
    
    # DEMO SEED for high trust
    print("DEMO SEED: Injecting realistic completed jobs for verified workers to reach >= 70 trust...")
    from app.models.worker import Worker, VerificationStatus, AvailabilityStatus
    from app.models.booking import Booking, BookingStatus
    from app.models.service_request import ServiceRequest
    from app.models.user import User, UserRole
    from app.services.auth import hash_password
    
    
    db = SessionLocal()
    try:
        workers = db.query(Worker).all()
        for w in workers:
            # Create a separate request per booking to be realistic
            for i in range(12): 
                req = ServiceRequest(
                    customer_id=2, service_id=1, cooperative_id=1,
                    description=f"Fix issue {i}", location="Noida", 
                    preferred_date="2026-10-04", preferred_time="10:00:00",
                    status="COMPLETED"
                )
                db.add(req)
                db.flush()
                
                b = Booking(
                    request_id=req.id, worker_id=w.id, assigned_by=1, status=BookingStatus.COMPLETED,
                    amount=500, scheduled_date="2026-10-04", scheduled_time="10:00:00",
                    customer_rating=5, 
                    arrived_at=datetime.datetime.strptime("2026-10-04 09:55:00", "%Y-%m-%d %H:%M:%S"), 
                    proof_of_work_hash=uuid.uuid4().hex
                )
                db.add(b)
            
            w.peer_votes = 3
            w.verification_status = VerificationStatus.VERIFIED
            db.commit()
            
            # Use real computation
            from app.services.trust_score import calculate_trust_score
            trust = calculate_trust_score(db, w)
            print(f"Worker {w.user.name} ({w.profession}): Trust Score = {trust['composite_trust_score']}")
            
        u = User(name="Pending", email="pending@test.com", password_hash=hash_password("pw"), role=UserRole.WORKER, is_active=True)
        db.add(u)
        db.flush()
        pw = Worker(user_id=u.id, cooperative_id=1, profession="Plumber", availability=AvailabilityStatus.AVAILABLE, verification_status=VerificationStatus.PENDING, peer_votes=0, rating=0.0, total_jobs=0)
        db.add(pw)
        db.commit()
    finally:
        db.close()
    
    print("\nCalling POST /login for demo accounts...")
    def try_login(email, pwd):
        res = client.post("/api/auth/login", data={"username": email, "password": pwd})
        print(f"Login {email}: HTTP {res.status_code}")
        
    try_login("admin@sahakarsathi.demo", "Admin@1234")
    try_login("asha.customer@sahakarsathi.demo", "Customer@1234")
    try_login("vishal.electrician@sahakarsathi.demo", "Worker@1234")

if __name__ == "__main__":
    main()

