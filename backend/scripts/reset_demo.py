import sys
import os

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
    # we can just call the seed logic or run it
    import scripts.seed_demo_data
    scripts.seed_demo_data.seed_demo_data()
    
    print("\nCalling POST /login for demo accounts...")
    
    def try_login(email, pwd):
        res = client.post("/api/auth/login", data={"username": email, "password": pwd})
        print(f"Login {email}: HTTP {res.status_code}")
        
    try_login("admin@sahakarsathi.demo", "Admin@1234")
    try_login("asha.customer@sahakarsathi.demo", "Customer@1234")
    try_login("vishal.electrician@sahakarsathi.demo", "Worker@1234")

if __name__ == "__main__":
    main()
