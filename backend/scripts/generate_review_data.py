"""
Synthetic Review and Rating Fraud Dataset Generator.

Generates 4,000 synthetic service reviews:
- ~3,700 legitimate customer reviews following realistic operational distributions.
- ~300 anomalous / fraudulent review patterns (collusion bursts, competitor sabotage,
  empty-text 5-star spam, extreme rating divergence from worker baseline).
"""
from pathlib import Path
import numpy as np
import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "ml_data"
OUTPUT_FILE = OUTPUT_DIR / "review_fraud_data.csv"


def generate_review_fraud_dataset(n_samples: int = 4000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_anomalies = int(n_samples * 0.08)  # 8% contamination
    n_normal = n_samples - n_anomalies

    # ---- 1. Normal Legitimate Reviews ----
    normal_ratings = rng.choice([3.0, 4.0, 4.5, 5.0], size=n_normal, p=[0.10, 0.25, 0.35, 0.30])
    normal_text_lens = rng.normal(loc=85.0, scale=35.0, size=n_normal).clip(15, 450).astype(int)
    normal_amounts = rng.normal(loc=650.0, scale=250.0, size=n_normal).clip(200, 2500).astype(float)
    normal_tenures = rng.integers(low=30, high=600, size=n_normal)
    normal_recent_counts = rng.poisson(lam=4.0, size=n_normal).clip(1, 15)
    normal_deviations = rng.exponential(scale=0.35, size=n_normal).clip(0.0, 1.2)

    df_normal = pd.DataFrame({
        "rating_value": normal_ratings,
        "review_length": normal_text_lens,
        "booking_amount": normal_amounts,
        "worker_tenure_days": normal_tenures,
        "worker_recent_booking_count": normal_recent_counts,
        "rating_deviation_from_worker_mean": normal_deviations,
        "is_fraud_label": 0,
    })

    # ---- 2. Anomalous / Fraudulent Reviews ----
    # Sub-type A: Fast Collusion Burst (5-star, 0-2 char text, brand new worker tenure < 5 days, 0 recent bookings)
    nA = n_anomalies // 3
    ratings_A = np.full(nA, 5.0)
    lens_A = rng.integers(low=0, high=4, size=nA)
    amounts_A = rng.uniform(low=100.0, high=250.0, size=nA)
    tenures_A = rng.integers(low=1, high=6, size=nA)
    recent_A = rng.integers(low=15, high=35, size=nA)  # unnatural velocity
    dev_A = rng.uniform(low=0.0, high=0.5, size=nA)

    # Sub-type B: Competitor Sabotage / Review Bombing (1-star, high rating deviation > 3.0, high amount)
    nB = n_anomalies // 3
    ratings_B = np.full(nB, 1.0)
    lens_B = rng.integers(low=5, high=25, size=nB)
    amounts_B = rng.uniform(low=150.0, high=350.0, size=nB)
    tenures_B = rng.integers(low=100, high=500, size=nB)
    recent_B = rng.integers(low=1, high=5, size=nB)
    dev_B = rng.uniform(low=2.8, high=4.0, size=nB)  # huge drop from worker's ~4.8 baseline

    # Sub-type C: Suspicious High-Volume Micro-Booking Spam
    nC = n_anomalies - nA - nB
    ratings_C = rng.choice([1.0, 5.0], size=nC)
    lens_C = rng.integers(low=0, high=8, size=nC)
    amounts_C = rng.uniform(low=80.0, high=150.0, size=nC)
    tenures_C = rng.integers(low=10, high=80, size=nC)
    recent_C = rng.integers(low=20, high=40, size=nC)
    dev_C = rng.uniform(low=1.5, high=3.5, size=nC)

    df_anomalies = pd.DataFrame({
        "rating_value": np.concatenate([ratings_A, ratings_B, ratings_C]),
        "review_length": np.concatenate([lens_A, lens_B, lens_C]),
        "booking_amount": np.concatenate([amounts_A, amounts_B, amounts_C]),
        "worker_tenure_days": np.concatenate([tenures_A, tenures_B, tenures_C]),
        "worker_recent_booking_count": np.concatenate([recent_A, recent_B, recent_C]),
        "rating_deviation_from_worker_mean": np.concatenate([dev_A, dev_B, dev_C]),
        "is_fraud_label": 1,
    })

    df = pd.concat([df_normal, df_anomalies], ignore_index=True)
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_review_fraud_dataset(4000, seed=42)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Generated {len(df)} review fraud samples ({df['is_fraud_label'].sum()} anomalies) -> {OUTPUT_FILE}")
