import sqlite3
import os


def run_migration():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'cooperative.db')
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for col, defn in [
        ('proof_tag', 'TEXT UNIQUE'),
        ('proof_lat', 'REAL'),
        ('proof_lon', 'REAL'),
        ('proof_captured_at', 'TEXT'),
        ('completion_code_tries', 'INTEGER NOT NULL DEFAULT 0'),
        ('started_at', 'TEXT'),
    ]:
        try:
            cur.execute(f"ALTER TABLE bookings ADD COLUMN {col} {defn}")
            print(f"Added column: {col}")
        except Exception as e:
            if 'duplicate column' in str(e).lower():
                print(f"Column already exists: {col}")
            elif 'cannot add a unique column' in str(e).lower():
                cur.execute(f"ALTER TABLE bookings ADD COLUMN {col} TEXT")
                cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS uq_bookings_{col} ON bookings({col})")
                print(f"Added column with unique index: {col}")
            else:
                raise
    conn.commit()
    conn.close()


if __name__ == '__main__':
    run_migration()
