"""
Demo Data Seeder for Cooperative Gig Services Platform.

Seeds:
1. Admin user (admin@coopserve.demo / Admin@1234)
2. Primary Cooperative ("Ghaziabad Community Services Cooperative")
3. Service Catalog items (Plumbing, Electrical, Cleaning, Carpentry, Painting, AC Servicing)
4. 7 realistic demo workers with diverse professions, experience, availability, ratings, and verification statuses.

Usage:
    python scripts/seed_demo_data.py
"""
import os
import sys

# Allow running from backend/ or project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import Base, SessionLocal, engine
import app.models  # noqa: F401
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.auth import create_admin_if_absent, get_user_by_email, hash_password
from app.services.cooperative import ensure_demo_cooperative
from app.services.service_catalog import ensure_seed_services

ADMIN_NAME = os.environ.get("ADMIN_NAME", "Cooperative Admin")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@coopserve.demo")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@1234")

DEMO_WORKERS = [
    {
        "name": "Rahul Kumar",
        "email": "rahul.electrician@coopserve.demo",
        "phone": "+91 98765 43210",
        "profession": "Electrician",
        "experience_years": 5,
        "location": "Sector 62, Noida",
        "skills": ["Wiring", "Fan Repair", "Switch Repair", "MCB Installation"],
        "availability": AvailabilityStatus.AVAILABLE,
        "availability_description": "Mon-Sat, 9:00 AM - 6:00 PM",
        "verification_status": VerificationStatus.VERIFIED,
        "rating": 4.8,
        "total_jobs": 5,
    },
    {
        "name": "Amit Verma",
        "email": "amit.electrician@coopserve.demo",
        "phone": "+91 97111 22334",
        "profession": "Electrician",
        "experience_years": 2,
        "location": "Sector 61, Noida",
        "skills": ["Wiring", "Light Fitting"],
        "availability": AvailabilityStatus.AVAILABLE,
        "availability_description": "Mon-Fri, 9:00 AM - 5:00 PM",
        "verification_status": VerificationStatus.VERIFIED,
        "rating": 4.2,
        "total_jobs": 25,
    },
    {
        "name": "Vikas Singh",
        "email": "vikas.electrician@coopserve.demo",
        "phone": "+91 96555 44332",
        "profession": "Electrician",
        "experience_years": 7,
        "location": "Sector 15, Noida",
        "skills": ["AC Wiring", "Industrial Wiring", "Transformer Fitting"],
        "availability": AvailabilityStatus.AVAILABLE,
        "availability_description": "Flexible hours",
        "verification_status": VerificationStatus.VERIFIED,
        "rating": 4.9,
        "total_jobs": 40,
    },
    {
        "name": "Sunita Devi",
        "email": "sunita.cleaning@coopserve.demo",
        "phone": "+91 98123 45678",
        "profession": "Cleaner",
        "experience_years": 4,
        "location": "Indirapuram, Ghaziabad",
        "skills": ["Deep Cleaning", "Sanitization", "Kitchen Cleaning"],
        "availability": AvailabilityStatus.AVAILABLE,
        "availability_description": "All days, 8:00 AM - 4:00 PM",
        "verification_status": VerificationStatus.VERIFIED,
        "rating": 4.9,
        "total_jobs": 18,
    },
    {
        "name": "Suresh Pal",
        "email": "suresh.plumber@coopserve.demo",
        "phone": "+91 95444 33221",
        "profession": "Plumber",
        "experience_years": 6,
        "location": "Sector 62, Noida",
        "skills": ["Pipe Fitting", "Leak Repair", "Drainage", "Tap Replacement"],
        "availability": AvailabilityStatus.AVAILABLE,
        "availability_description": "Mon-Sat, 10:00 AM - 7:00 PM",
        "verification_status": VerificationStatus.VERIFIED,
        "rating": 4.7,
        "total_jobs": 12,
    },
    {
        "name": "Ramesh Gupta",
        "email": "ramesh.painter@coopserve.demo",
        "phone": "+91 94333 22110",
        "profession": "Painter",
        "experience_years": 10,
        "location": "Vasundhara, Ghaziabad",
        "skills": ["Interior Painting", "Wall Texture", "Waterproofing"],
        "availability": AvailabilityStatus.AVAILABLE,
        "availability_description": "Flexible hours",
        "verification_status": VerificationStatus.PENDING,
        "rating": 0.0,
        "total_jobs": 0,
    },
    {
        "name": "Mohd. Salim",
        "email": "salim.ac@coopserve.demo",
        "phone": "+91 93222 11009",
        "profession": "AC Technician",
        "experience_years": 6,
        "location": "Sector 18, Noida",
        "skills": ["AC Servicing", "Gas Refilling", "Compressor Repair"],
        "availability": AvailabilityStatus.UNAVAILABLE,
        "availability_description": "Unavailable",
        "verification_status": VerificationStatus.REJECTED,
        "rating": 0.0,
        "total_jobs": 0,
    },
]


def seed_demo_data():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed Admin
        admin = create_admin_if_absent(
            db,
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
        )
        print(f"[OK] Admin account ready: {admin.email}")

        # 2. Seed Primary Cooperative
        coop = ensure_demo_cooperative(db, admin_id=admin.id)
        print(f"[OK] Primary Cooperative ready: {coop.name} ({coop.location})")

        # 3. Seed Service Catalog
        services = ensure_seed_services(db)
        print(f"[OK] Service Catalog seeded: {len(services)} services active")

        # 4. Seed Demo Workers
        created_workers = 0
        for data in DEMO_WORKERS:
            existing_user = get_user_by_email(db, data["email"])
            if not existing_user:
                # Create User record
                user = User(
                    name=data["name"],
                    email=data["email"],
                    phone=data["phone"],
                    password_hash=hash_password("Worker@1234"),
                    role=UserRole.WORKER,
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)

                # Create Worker Profile record linked to user & coop
                worker = Worker(
                    user_id=user.id,
                    cooperative_id=coop.id,
                    profession=data["profession"],
                    experience_years=data["experience_years"],
                    location=data["location"],
                    skills=data["skills"],
                    availability=data["availability"],
                    availability_description=data["availability_description"],
                    verification_status=data["verification_status"],
                    rating=data["rating"],
                    total_jobs=data["total_jobs"],
                )
                db.add(worker)
                db.commit()
                created_workers += 1
            else:
                # Ensure existing demo worker is linked to coop
                if existing_user.worker_profile and not existing_user.worker_profile.cooperative_id:
                    existing_user.worker_profile.cooperative_id = coop.id
                    db.commit()

        print(f"[OK] Demo Workers processed ({created_workers} new workers created)")

        # 5. Seed Demo Customers & Sample Service Requests
        c1 = get_user_by_email(db, "asha.customer@coopserve.demo")
        if not c1:
            c1 = User(
                name="Asha Sharma",
                email="asha.customer@coopserve.demo",
                phone="+91 98765 00000",
                password_hash=hash_password("Customer@1234"),
                role=UserRole.CUSTOMER,
                is_active=True,
            )
            db.add(c1)
            db.commit()
            db.refresh(c1)

        c2 = get_user_by_email(db, "rohit.customer@coopserve.demo")
        if not c2:
            c2 = User(
                name="Rohit Verma",
                email="rohit.customer@coopserve.demo",
                phone="+91 98765 11111",
                password_hash=hash_password("Customer@1234"),
                role=UserRole.CUSTOMER,
                is_active=True,
            )
            db.add(c2)
            db.commit()
            db.refresh(c2)
            print("[OK] Demo Customers ready: Asha Sharma & Rohit Verma")

        # Seed sample requests for demo customer if none exist
        from app.models.service_request import RequestStatus, ServiceRequest
        existing_reqs = db.query(ServiceRequest).filter(ServiceRequest.customer_id == c1.id).count()
        if existing_reqs == 0 and len(services) >= 2:
            req1 = ServiceRequest(
                customer_id=c1.id,
                service_id=services[0].id,  # Electrical / Plumbing
                cooperative_id=coop.id,
                description="Ceiling fan is making noise and needs urgent maintenance.",
                location="Sector 62, Noida",
                preferred_date="2026-08-27",
                preferred_time="14:00",
                status=RequestStatus.PENDING,
            )
            req2 = ServiceRequest(
                customer_id=c1.id,
                service_id=services[2].id if len(services) > 2 else services[1].id,
                cooperative_id=coop.id,
                description="Deep kitchen cleaning and sanitization required before weekend event.",
                location="Sector 62, Noida",
                preferred_date="2026-08-28",
                preferred_time="10:00",
                status=RequestStatus.PENDING,
            )
            db.add(req1)
            db.add(req2)
            db.commit()
            print("[OK] Sample Service Requests seeded for demo customer")

        print("-" * 60)
        print("Demo Environment Ready:")
        print(f"  Cooperative   : {coop.name}")
        print(f"  Admin Email   : {ADMIN_EMAIL}")
        print(f"  Admin Pass    : {ADMIN_PASSWORD}")
        print(f"  Customer Email: asha.customer@coopserve.demo")
        print(f"  Customer Pass : Customer@1234")
        print(f"  Worker Pass   : Worker@1234 (for all demo worker accounts)")
        print("-" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
