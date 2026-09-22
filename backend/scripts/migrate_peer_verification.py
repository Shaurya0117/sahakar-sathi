"""
Database migration script for Peer Verification Feature.

Adds new peer_votes column to the workers table.
SQLite supports ALTER TABLE ADD COLUMN — safe to run multiple times.
"""
import sqlite3
import os

DB_PATHS = [
    os.path.join(os.path.dirname(__file__), '..', 'cooperative.db'),
    os.path.join(os.path.dirname(__file__), '..', '..', 'cooperative.db'),
]

def find_db():
    for path in DB_PATHS:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None

def migrate():
    db_path = find_db()
    if not db_path:
        print("Database file not found.")
        return

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(workers)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    if 'peer_votes' not in existing_columns:
        try:
            cursor.execute("ALTER TABLE workers ADD COLUMN peer_votes TEXT DEFAULT '[]'")
            print("  [OK] Added 'peer_votes' column to workers table")
        except Exception as e:
            print(f"  [WARN] peer_votes: {e}")
    else:
        print("  - peer_votes already exists")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
