"""
Migration script: Create micro_loans and cooperative_proposals tables,
and seed demo governance proposals.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.session import engine, SessionLocal, Base
# Import ALL models so SQLAlchemy metadata knows about them
from app.models.user import User
from app.models.worker import Worker
from app.models.cooperative import Cooperative
from app.services.microcredit import MicroLoan
from app.services.governance import CooperativeProposal
from sqlalchemy import inspect

def migrate():
    inspector = inspect(engine)
    existing = inspector.get_table_names()

    # Create tables
    MicroLoan.__table__.create(bind=engine, checkfirst=True)
    CooperativeProposal.__table__.create(bind=engine, checkfirst=True)
    print("[OK] Tables created: micro_loans, cooperative_proposals")

    # Seed demo proposals
    db = SessionLocal()
    count = db.query(CooperativeProposal).count()
    if count == 0:
        proposals = [
            CooperativeProposal(
                title="Increase Worker Share from 82% to 85%",
                description="Proposal to increase the worker's share of each payment from 82% to 85%, reducing the cooperative fund contribution from 18% to 15%.",
                category="Pricing",
                created_by=1,
            ),
            CooperativeProposal(
                title="Add Festival Bonus for Diwali Season",
                description="Approve a ₹500 Diwali bonus for every worker who completes 10+ jobs in October. Funded from the cooperative surplus fund.",
                category="Policy",
                created_by=1,
            ),
            CooperativeProposal(
                title="Mandatory Safety Training for New Members",
                description="All new cooperative members must complete a 2-hour safety and customer etiquette training before accepting their first job.",
                category="Membership",
                created_by=1,
            ),
        ]
        db.add_all(proposals)
        db.commit()
        print(f"[OK] Seeded {len(proposals)} demo governance proposals")
    else:
        print(f"[SKIP] {count} proposals already exist")
    db.close()

if __name__ == "__main__":
    migrate()
