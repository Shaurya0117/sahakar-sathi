import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "database.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating local_shops table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS local_shops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        location VARCHAR(255) NOT NULL,
        inventory_json TEXT DEFAULT '{}'
    )
    """)

    print("Creating household_appliances table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS household_appliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        appliance_type VARCHAR(100) NOT NULL,
        brand VARCHAR(100),
        purchase_year INTEGER,
        last_serviced_date TIMESTAMP,
        health_score FLOAT DEFAULT 100.0,
        predicted_failure_days INTEGER,
        reserved_part VARCHAR(255),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Seed some local shops for the demo
    cursor.execute("SELECT COUNT(*) FROM local_shops")
    if cursor.fetchone()[0] == 0:
        print("Seeding local shops...")
        cursor.execute("INSERT INTO local_shops (name, location, inventory_json) VALUES (?, ?, ?)", 
                       ("Sharma Electricals", "Ghaziabad", '{"AC Compressor": 5, "Fan Motor": 10, "Copper Pipe": 50}'))
        cursor.execute("INSERT INTO local_shops (name, location, inventory_json) VALUES (?, ?, ?)", 
                       ("Gupta Hardware", "Noida", '{"Water Pump": 3, "AC Gas": 15, "Switchboard": 20}'))

    conn.commit()
    conn.close()
    print("Migration for Predictive Logistics complete.")

if __name__ == "__main__":
    migrate()
