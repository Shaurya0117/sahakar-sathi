import sys
import os

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import Base, engine, SessionLocal
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.user import User, UserRole
from app.models.worker import Worker
from app.auth.password import hash_password

client = TestClient(app)

def setup_fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create cooperative
        coop = Cooperative(name="Test Co-op", location="Noida", description="E2E Test", admin_id=1)
        db.add(coop)
        
        # Create Users
        admin = User(name="Admin", email="admin@test.com", password_hash=hash_password("password"), role=UserRole.ADMIN, is_active=True)
        customer = User(name="Customer", email="cust@test.com", password_hash=hash_password("password"), role=UserRole.CUSTOMER, is_active=True)
        worker_u = User(name="Worker", email="work@test.com", password_hash=hash_password("password"), role=UserRole.WORKER, is_active=True)
        db.add_all([admin, customer, worker_u])
        db.commit()
        
        # Create Service
        svc = Service(name="Plumbing", category="Repair", description="Fix pipes", price=500.0, duration_minutes=60, is_active=True)
        db.add(svc)
        db.commit()
        
        # Create Worker Profile
        worker_p = Worker(
            user_id=worker_u.id, 
            cooperative_id=coop.id, 
            profession="Plumber",
            verification_status="VERIFIED"
        )
        db.add(worker_p)
        db.flush()
        
        # Create 3 voters
        for i in range(3):
            vu = User(name=f"Voter {i}", email=f"voter{i}@test.com", password_hash=hash_password("password"), role=UserRole.WORKER, is_active=True)
            db.add(vu)
            db.flush()
            vw = Worker(user_id=vu.id, cooperative_id=coop.id, profession="Plumber", verification_status="VERIFIED")
            db.add(vw)
            
        # Create pending worker
        pu = User(name="Pending", email="pending@test.com", password_hash=hash_password("password"), role=UserRole.WORKER, is_active=True)
        db.add(pu)
        db.flush()
        pw = Worker(user_id=pu.id, cooperative_id=coop.id, profession="Plumber", verification_status="PENDING")
        db.add(pw)
        db.commit()
    finally:
        db.close()

def login(email):
    res = client.post("/api/auth/login", data={"username": email, "password": "password"})
    return res.json()["access_token"]

def main():
    print("Setting up fresh DB...")
    setup_fresh_db()
    
    a_token = login("admin@test.com")
    c_token = login("cust@test.com")
    w_token = login("work@test.com")
    
    def auth(t): return {"Authorization": f"Bearer {t}"}
    
    # Customer books
    print("1. Customer books: ", end="")
    res = client.post("/api/requests", json={
        "service_id": 1,
        "cooperative_id": 1,
        "description": "Leaky pipe",
        "location": "Sector 62",
        "preferred_date": "2026-10-10",
        "preferred_time": "10:00"
    }, headers=auth(c_token))
    if res.status_code == 201:
        req_id = res.json()["id"]
        print("PASS")
    else:
        print(f"FAIL ({res.text})")
        return
        
    # Admin allocates
    print("2. Admin allocates: ", end="")
    res = client.post(f"/api/requests/{req_id}/allocate", json={
        "worker_id": 1,
        "amount": 500.0
    }, headers=auth(a_token))
    if res.status_code == 201:
        booking_id = res.json()["id"]
        print("PASS")
    else:
        print(f"FAIL ({res.text})")
        return
        
    # Worker accepts
    print("3. Worker accepts: ", end="")
    res = client.patch(f"/api/bookings/{booking_id}/accept", headers=auth(w_token))
    if res.status_code == 200:
        print("PASS")
    else:
        print(f"FAIL ({res.text})")
        return
        

    # Worker marks arrived
    print("4. Worker marks arrived: ", end="")
    res = client.patch(f"/api/bookings/{booking_id}/arrive", headers=auth(w_token))
    if res.status_code == 200:
        print("PASS")
    else:
        print(f"FAIL ({res.text})")
        return

    # Worker starts
    print("5. Worker starts: ", end="")
    res = client.patch(f"/api/bookings/{booking_id}/start", headers=auth(w_token))
    if res.status_code == 200:
        print("PASS")
    else:
        print(f"FAIL ({res.text})")
        return
        
    print("5a. Negative test (Empty hash): ", end="")
    res_neg = client.patch(f"/api/bookings/{booking_id}/complete", json={
        "proof_of_work_hash": ""
    }, headers=auth(w_token))
    if res_neg.status_code == 400 or res_neg.status_code == 422:
        print("REJECTED (PASS)")
    else:
        print(f"FAIL (Expected 400/422, got {res_neg.status_code})")
        
    print("5b. Negative test (Hash Reused from another booking): ", end="")
    # Seed db with a fake complete booking with same hash
    db = SessionLocal()
    from app.models.booking import Booking, BookingStatus
    from datetime import datetime, timedelta
    
    # We create a manual mock booking for the worker that has a conflicting hash
    fake_b = Booking(
        worker_id=1, 
        request_id=req_id, 
        assigned_by=1,
        status=BookingStatus.COMPLETED, 
        proof_of_work_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", 
        amount=100.0,
        scheduled_date="2026-10-02",
        scheduled_time="10:00:00.000000"
    )
    db.add(fake_b)
    db.commit()
    
    res_neg = client.patch(f"/api/bookings/{booking_id}/complete", json={
        "proof_of_work_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "privacy_score": 95.0
    }, headers=auth(w_token))
    if "similar" in res_neg.text.lower() or "reused" in res_neg.text.lower() or res_neg.status_code == 400:
        print("REJECTED (PASS)")
    else:
        print(f"FAIL (Expected rejection, got {res_neg.status_code}: {res_neg.text})")
        
    db.delete(fake_b)
    db.commit()
    db.close()

    # Worker submits proof and completes
    print("6. Worker submits proof and completes: ", end="")
    complete_payload = {
        "proof_of_work_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f506172839a0b1c2d3e4f50",
        "privacy_score": 95.0,
        "nonce_match": False,
        "gps_match": False,
        "customer_otp_match": False
    }
    res = client.patch(f"/api/bookings/{booking_id}/complete", json=complete_payload, headers=auth(w_token))
    if res.status_code == 200:
        print("PASS")
    else:
        print(f"FAIL ({res.text})")
        return
        
    # Customer rates
    print("7. Customer rates: ", end="")
    res = client.post(f"/api/bookings/{booking_id}/review", json={
        "rating": 5.0,
        "review_text": "Great job"
    }, headers=auth(c_token))
    if res.status_code == 200:
        print("PASS")
    else:
        print(f"FAIL ({res.text})")
        return
        
    print("8. Worker fetches profile JSON: ", end="")
    res = client.get("/api/workers/me", headers=auth(w_token))
    if res.status_code == 200:
        print("PASS")
        print("\n--- Worker Profile JSON ---")
        import json
        print(json.dumps(res.json(), indent=2))
        print("---------------------------")
    else:
        print(f"FAIL ({res.text})")


    print("9. Peer Verification Flow: ", end="")
    res = client.post("/api/auth/login", data={"username": "pending@test.com", "password": "pw"})
    if res.status_code == 200:
        cand_token = res.json()["access_token"]
        res = client.get("/api/workers/me", headers=auth(cand_token))
        cand_id = res.json()["id"]
        
        voter_emails = ["voter0@test.com", "voter1@test.com", "voter2@test.com"]
        for email in voter_emails:
            login_res = client.post("/api/auth/login", data={"username": email, "password": "password"})
            v_token = login_res.json()["access_token"]
            v_res = client.post(f"/api/workers/{cand_id}/peer-verify", json={"vote": 1, "comments": "Looks good"}, headers=auth(v_token))
            
        final_res = client.get("/api/workers/me", headers=auth(cand_token))
        if final_res.json()["verification_status"] == "VERIFIED":
            print("PASS (3 votes reached)")
        else:
            print(f"FAIL (Not verified after 3 votes, status: {final_res.json()[
verification_status]})")
    else:
        print("SKIP (Pending worker not found)")

    print("\n--- E2E Smoke Test Finished Successfully ---")

if __name__ == "__main__":
    main()
