import httpx
import time
import sys
sys.path.append('.')
from app.database.session import SessionLocal
from app.models.worker import Worker

base_url = "http://127.0.0.1:8000"

def get_token(email):
    res = httpx.post(f"{base_url}/api/auth/login", data={"username": email, "password": "Worker@1234"})
    if res.status_code != 200:
        print(f"Failed to login {email}: {res.json()}")
        return None
    return res.json()["access_token"]

db = SessionLocal()
verified_workers = db.query(Worker).filter(Worker.verification_status == 'VERIFIED').limit(3).all()
workers = [w.user.email for w in verified_workers]

# Get candidate ID
token1 = get_token(workers[0])
res = httpx.get(f"{base_url}/api/peer-verification/candidates", headers={"Authorization": f"Bearer {token1}"})
candidates = res.json()
if not candidates:
    print("No candidates found!")
    exit(1)
candidate_id = candidates[0]["worker_id"]
print(f"Candidate ID: {candidate_id}")

for email in workers:
    token = get_token(email)
    print(f"Worker {email} voting for candidate {candidate_id}")
    res = httpx.post(
        f"{base_url}/api/peer-verification/vote",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate_id, "is_positive": True}
    )
    print(res.status_code, res.text)

# Wait a second for processing
time.sleep(1)

# Check final status
w = db.query(Worker).filter(Worker.id == candidate_id).first()
print(f"Candidate Final Status: {w.verification_status.name if hasattr(w.verification_status, 'name') else w.verification_status}")
