"""
Admin seeder — creates the first ADMIN account if it doesn't exist.

Usage (from backend/ directory with venv activated):

    python scripts/seed_admin.py

Demo credentials (override via environment variables):

    ADMIN_EMAIL    — default: admin@coopserve.demo
    ADMIN_NAME     — default: Cooperative Admin
    ADMIN_PASSWORD — default: Admin@1234  ← change before any real demo!

IMPORTANT: Do NOT commit real credentials. Use .env or environment variables.
"""
import os
import sys

# Allow running from backend/ or project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import Base, SessionLocal, engine
import app.models  # noqa: F401 — registers all models with Base
from app.services.auth import create_admin_if_absent

# ── Demo credentials (override via env vars) ──────────────────────────────────
ADMIN_NAME = os.environ.get("ADMIN_NAME", "Cooperative Admin")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@coopserve.demo")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@1234")


def seed():
    print("Creating database tables (if not exist)…")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = create_admin_if_absent(
            db,
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
        )
        print(f"Admin ready: id={admin.id}  email={admin.email}")
        print("-" * 50)
        print("Demo credentials:")
        print(f"  Email   : {ADMIN_EMAIL}")
        print(f"  Password: {ADMIN_PASSWORD}")
        print("-" * 50)
        print("WARNING: Change ADMIN_PASSWORD before any real demo or deployment!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
