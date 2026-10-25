"""
Generate 5,000 synthetic worker churn samples for training.
Saves to backend/ml_data/churn_data.csv.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure the project root is importable
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

OUTPUT_DIR = BACKEND_DIR / "ml_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "churn_data.csv"

SEED = 42
N_SAMPLES = 5000

rng = np.random.default_rng(SEED)

days_since_last_booking = rng.uniform(0, 90, N_SAMPLES)
bookings_last_30d = rng.integers(0, 21, N_SAMPLES)
earnings_last_30d = rng.uniform(0, 15000, N_SAMPLES)
acceptance_rate = rng.uniform(0.0, 1.0, N_SAMPLES)
avg_fatigue_index = rng.uniform(0.0, 95.0, N_SAMPLES)
rating = rng.uniform(1.0, 5.0, N_SAMPLES)
experience_years = rng.integers(0, 16, N_SAMPLES)
days_on_platform = rng.integers(1, 1001, N_SAMPLES)
earnings_trend = rng.uniform(-1.0, 1.0, N_SAMPLES)

noise = rng.normal(0, 0.5, N_SAMPLES)

logit = (
    2.1
    + 0.05 * days_since_last_booking
    - 0.15 * bookings_last_30d
    - 0.0002 * earnings_last_30d
    - 2.0 * acceptance_rate
    + 0.015 * avg_fatigue_index
    - 0.3 * rating
    - 0.04 * experience_years
    - 0.001 * days_on_platform
    - 1.5 * earnings_trend
    + noise
)

prob_churn = 1.0 / (1.0 + np.exp(-logit))
churned = (prob_churn > 0.5).astype(int)

df = pd.DataFrame({
    "days_since_last_booking": days_since_last_booking,
    "bookings_last_30d": bookings_last_30d,
    "earnings_last_30d": earnings_last_30d,
    "acceptance_rate": acceptance_rate,
    "avg_fatigue_index": avg_fatigue_index,
    "rating": rating,
    "experience_years": experience_years,
    "days_on_platform": days_on_platform,
    "earnings_trend": earnings_trend,
    "churned": churned,
})

df.to_csv(OUTPUT_PATH, index=False)

churn_rate = churned.mean() * 100
print(f"Saved {N_SAMPLES} samples to {OUTPUT_PATH}")
print(f"Churn rate: {churn_rate:.1f}%")
