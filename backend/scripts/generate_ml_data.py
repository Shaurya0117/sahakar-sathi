"""
Synthetic Data Generation for Sahakar Sathi ML Module.

Hidden Logistic Rule for Worker Acceptance:
------------------------------------------
Let z be the latent log-odds of a worker accepting a dispatched service job:
  z = 0.25
      - 0.15 * (distance_km - 4.0)
      + 0.020 * (skill_match_score - 80.0)
      - 0.035 * (fatigue_index - 30.0)
      + 0.50 * (rating - 4.0)
      + 0.040 * (experience_years - 5.0)
      - 0.00015 * (recent_earnings - 2500.0)
      + 0.0030 * (job_value - 500.0)
      - 1.20 * (job_intensity - 0.65)
      - 0.15 * max(0, hour_of_day - 18)
      + 2.00 * (past_acceptance_rate - 0.75)
      - 0.0050 * ((distance_km - 4.0) * (fatigue_index - 30.0))  [Interaction Term]
      + epsilon, where epsilon ~ Normal(0, 0.5^2)

The probability of acceptance is:
  P(accepted = 1) = 1 / (1 + exp(-z))
A worker accepts if P(accepted = 1) > 0.5.

Hidden Duration Rule:
--------------------
Baseline duration by service type:
  - plumbing: 1.8 hrs
  - carpentry: 2.5 hrs
  - painting: 3.5 hrs
  - electrical: 1.5 hrs
  - repair: 2.0 hrs
  - ac: 2.2 hrs
  - cleaning: 3.0 hrs
  - general: 1.2 hrs

Duration = baseline * (1 + 0.45 * (job_intensity - 0.65))
                    * (0.75 + 0.5 * (job_value / 550.0))
                    * (1.0 - 0.02 * min(12, experience_years))
                    + epsilon, where epsilon ~ Normal(0, 0.3^2)
Clipped strictly to [0.5, 8.0] hours.
"""

import os
import numpy as np
import pandas as pd

RANDOM_SEED = 42

def generate_acceptance_data(n_samples: int = 30000, n_sim_seeds: int = 100, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    
    # Simulation seed per row (for grouped cross-validation without leakage)
    sim_seeds = rng.integers(0, n_sim_seeds, size=n_samples)
    
    distance_km = rng.exponential(scale=4.0, size=n_samples).clip(0.5, 25.0)
    skill_match_score = rng.uniform(50.0, 100.0, size=n_samples)
    fatigue_index = (rng.beta(2.0, 3.0, size=n_samples) * 85.0).clip(0.0, 100.0)
    rating = rng.uniform(3.0, 5.0, size=n_samples)
    experience_years = rng.integers(0, 16, size=n_samples)
    recent_earnings = rng.uniform(0.0, 7500.0, size=n_samples)
    job_value = rng.uniform(300.0, 800.0, size=n_samples)
    job_intensity = rng.choice([0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85], size=n_samples)
    hour_of_day = rng.integers(6, 23, size=n_samples)  # 6 to 22
    past_acceptance_rate = rng.beta(6.0, 2.0, size=n_samples).clip(0.0, 1.0)
    
    # Latent log-odds with non-linear penalties and distance-fatigue interaction
    evening_penalty = np.maximum(0, hour_of_day - 18)
    interaction_term = (distance_km - 4.0) * (fatigue_index - 30.0)
    noise = rng.normal(0.0, 0.5, size=n_samples)
    
    z = (
        0.25
        - 0.15 * (distance_km - 4.0)
        + 0.020 * (skill_match_score - 80.0)
        - 0.035 * (fatigue_index - 30.0)
        + 0.50 * (rating - 4.0)
        + 0.040 * (experience_years - 5.0)
        - 0.00015 * (recent_earnings - 2500.0)
        + 0.0030 * (job_value - 500.0)
        - 1.20 * (job_intensity - 0.65)
        - 0.15 * evening_penalty
        + 2.00 * (past_acceptance_rate - 0.75)
        - 0.0050 * interaction_term
        + noise
    )
    
    prob = 1.0 / (1.0 + np.exp(-z))
    accepted = (prob > 0.5).astype(int)
    
    df = pd.DataFrame({
        "distance_km": np.round(distance_km, 2),
        "skill_match_score": np.round(skill_match_score, 1),
        "fatigue_index": np.round(fatigue_index, 1),
        "rating": np.round(rating, 2),
        "experience_years": experience_years,
        "recent_earnings": np.round(recent_earnings, 2),
        "job_value": np.round(job_value, 2),
        "job_intensity": np.round(job_intensity, 2),
        "hour_of_day": hour_of_day,
        "past_acceptance_rate": np.round(past_acceptance_rate, 3),
        "sim_seed": sim_seeds,
        "accepted": accepted,
    })
    return df


def generate_duration_data(n_samples: int = 15000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    
    service_types = ["plumbing", "carpentry", "painting", "electrical", "repair", "ac", "cleaning", "general"]
    base_hours_map = {
        "plumbing": 1.8,
        "carpentry": 2.5,
        "painting": 3.5,
        "electrical": 1.5,
        "repair": 2.0,
        "ac": 2.2,
        "cleaning": 3.0,
        "general": 1.2,
    }
    
    sampled_services = rng.choice(service_types, size=n_samples)
    base_hours = np.array([base_hours_map[s] for s in sampled_services])
    
    job_intensity = rng.choice([0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85], size=n_samples)
    experience_years = rng.integers(0, 16, size=n_samples)
    job_value = rng.uniform(300.0, 800.0, size=n_samples)
    
    # Efficiency effect: experience reduces completion time by up to ~24%
    exp_factor = 1.0 - 0.02 * np.minimum(12, experience_years)
    intensity_factor = 1.0 + 0.45 * (job_intensity - 0.65)
    value_factor = 0.75 + 0.5 * (job_value / 550.0)
    noise = rng.normal(0.0, 0.3, size=n_samples)
    
    raw_hours = base_hours * intensity_factor * value_factor * exp_factor + noise
    hours = np.clip(raw_hours, 0.5, 8.0)
    
    df = pd.DataFrame({
        "service_type": sampled_services,
        "job_intensity": np.round(job_intensity, 2),
        "experience_years": experience_years,
        "job_value": np.round(job_value, 2),
        "hours": np.round(hours, 2),
    })
    return df


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "..", "ml_data")
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating acceptance dataset (30,000 samples)...")
    df_acc = generate_acceptance_data()
    acc_path = os.path.join(output_dir, "acceptance_data.csv")
    df_acc.to_csv(acc_path, index=False)
    print(f"Saved: {acc_path}")
    print(f"Acceptance rate: {df_acc['accepted'].mean():.4f} ({df_acc['accepted'].sum()} / {len(df_acc)})")
    print("Acceptance features summary:")
    print(df_acc.describe().T[["min", "mean", "max"]])
    print("-" * 60)
    
    print("Generating duration dataset (15,000 samples)...")
    df_dur = generate_duration_data()
    dur_path = os.path.join(output_dir, "duration_data.csv")
    df_dur.to_csv(dur_path, index=False)
    print(f"Saved: {dur_path}")
    print(f"Mean duration: {df_dur['hours'].mean():.2f} hours (range: {df_dur['hours'].min():.2f} - {df_dur['hours'].max():.2f})")
    print("Duration per service type:")
    print(df_dur.groupby("service_type")["hours"].agg(["count", "mean", "std"]))


if __name__ == "__main__":
    main()
