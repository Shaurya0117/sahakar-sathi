import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database.session import engine, SessionLocal
from app.models.user import User
from app.models.worker import Worker
from app.models.cooperative import Cooperative
from app.models.timebank import TimeBankTransaction
from sqlalchemy import inspect, text

def migrate():
    # 1. Add fields to workers table
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE workers ADD COLUMN eshram_uan VARCHAR(50)"))
            conn.execute(text("ALTER TABLE workers ADD COLUMN digilocker_verified INTEGER DEFAULT 0"))
            conn.execute(text("ALTER TABLE workers ADD COLUMN government_benefits_linked TEXT DEFAULT '[]'"))
            conn.execute(text("ALTER TABLE workers ADD COLUMN time_credits FLOAT DEFAULT 0.0"))
            conn.commit()
            print("[OK] Added new columns to workers table")
        except Exception as e:
            print(f"Skipping worker columns alter (might already exist): {e}")
            conn.rollback()
            
    # 2. Create timebank_transactions table
    TimeBankTransaction.__table__.create(bind=engine, checkfirst=True)
    print("[OK] Created timebank_transactions table")

if __name__ == "__main__":
    migrate()
