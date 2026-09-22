"""
Database migration script for Patent Features.

Adds new columns to the workers table for Trust Score feature.
SQLite supports ALTER TABLE ADD COLUMN — safe to run multiple times.

Usage: python -m scripts.migrate_patent_features
"""
import sqlite3
import sys
import os

# Find the database file
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
        print("Database file not found. Skipping migration.")
        print("The columns will be created automatically when you run seed_demo_data.py")
        return

    print(f"Migrating database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(workers)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    print(f"Existing worker columns: {existing_columns}")

    # Add trust_score column if missing
    if 'trust_score' not in existing_columns:
        try:
            cursor.execute("ALTER TABLE workers ADD COLUMN trust_score REAL DEFAULT NULL")
            print("  [OK] Added 'trust_score' column to workers table")
        except Exception as e:
            print(f"  [WARN] trust_score: {e}")
    else:
        print("  - trust_score already exists")

    # Add trust_breakdown column if missing
    if 'trust_breakdown' not in existing_columns:
        try:
            cursor.execute("ALTER TABLE workers ADD COLUMN trust_breakdown TEXT DEFAULT NULL")
            print("  [OK] Added 'trust_breakdown' column to workers table")
        except Exception as e:
            print(f"  [WARN] trust_breakdown: {e}")
    else:
        print("  - trust_breakdown already exists")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
