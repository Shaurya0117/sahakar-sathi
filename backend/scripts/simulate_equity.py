import sys
sys.path.append('.')
import numpy as np
import matplotlib.pyplot as plt
import random
import math
import os

from app.services.matching.scorer import (
    WEIGHT_SKILL, WEIGHT_LOCATION, WEIGHT_AVAILABILITY,
    WEIGHT_RATING, WEIGHT_EXPERIENCE, WEIGHT_BIO_ECONOMIC
)

def gini(incomes):
    incomes = np.sort(incomes)
    n = len(incomes)
    index = np.arange(1, n + 1)
    if np.sum(incomes) == 0: return 0
    return ((np.sum((2 * index - n  - 1) * incomes)) / (n * np.sum(incomes)))

def dist(c1, c2):
    return math.hypot(c1[0] - c2[0], c1[1] - c2[1])

def run_simulation(strategy="equity", num_jobs=200, num_workers=7, seed=42):
    random.seed(seed)
    np.random.seed(seed)
    
    worker_earnings = np.zeros(num_workers)
    # Give workers random locations (x, y) between 0 and 10
    worker_locs = [(random.uniform(0, 10), random.uniform(0, 10)) for _ in range(num_workers)]
    # Give workers random skill sets (each worker has 2 to 4 skills out of 10)
    worker_skills = [set(random.sample(range(10), random.randint(2, 4))) for _ in range(num_workers)]
    # Random ratings 1 to 5
    worker_ratings = [random.uniform(1.0, 5.0) for _ in range(num_workers)]
    # Random experience 1 to 10
    worker_exp = [random.randint(1, 10) for _ in range(num_workers)]
    
    total_travel = 0
    total_skill_match = 0
    
    for job_id in range(num_jobs):
        job_value = random.randint(300, 800)
        job_loc = (random.uniform(0, 10), random.uniform(0, 10))
        job_skill = random.randint(0, 9)
        
        # Calculate distances for all workers
        dists = [dist(loc, job_loc) for loc in worker_locs]
        
        available = list(range(num_workers))
        
        if strategy == "nearest":
            # Pick the worker with minimum distance
            chosen = min(available, key=lambda w: dists[w])
        elif strategy == "nearest_with_skill":
            # Filter by skill, then pick nearest
            skilled = [w for w in available if job_skill in worker_skills[w]]
            if not skilled:
                skilled = available
            chosen = min(skilled, key=lambda w: dists[w])
        else: # "equity" - The real matcher
            max_earn = max(worker_earnings) if max(worker_earnings) > 0 else 1.0
            scores = []
            max_dist = 14.14 # sqrt(10^2 + 10^2)
            
            for w in available:
                # 1. Skill Score (0-100)
                skill_score = 100.0 if job_skill in worker_skills[w] else 0.0
                
                # 2. Location Score (0-100)
                d = min(dists[w], max_dist)
                location_score = max(0.0, 100.0 * (1 - d/max_dist))
                
                # 3. Bio-Economic (Equity/Workload) Score (0-100)
                # Lower earnings -> higher score
                equity_score = max(0.0, 100.0 * (1.0 - (worker_earnings[w] / max_earn)))
                
                # 4. Rating Score (0-100)
                rating_score = (worker_ratings[w] / 5.0) * 100.0
                
                # 5. Experience Score (0-100)
                exp_score = min(100.0, (worker_exp[w] / 10.0) * 100.0)
                
                # 6. Availability (assume 100 for simulation)
                avail_score = 100.0
                
                final_score = (
                    (skill_score * WEIGHT_SKILL) +
                    (location_score * WEIGHT_LOCATION) +
                    (equity_score * WEIGHT_BIO_ECONOMIC) +
                    (rating_score * WEIGHT_RATING) +
                    (exp_score * WEIGHT_EXPERIENCE) +
                    (avail_score * WEIGHT_AVAILABILITY)
                )
                scores.append(final_score)
                
            chosen = available[np.argmax(scores)]
            
        worker_earnings[chosen] += job_value
        total_travel += dists[chosen]
        total_skill_match += 1 if job_skill in worker_skills[chosen] else 0
        
    return worker_earnings, total_travel / num_jobs, total_skill_match / num_jobs

def generate_chart():
    baseline_ginis = []
    skill_baseline_ginis = []
    equity_ginis = []
    b_dists = []
    sb_dists = []
    e_dists = []
    b_skills = []
    sb_skills = []
    e_skills = []
    
    for i in range(20):
        b_earn, b_dist, b_skill = run_simulation("nearest", seed=i)
        sb_earn, sb_dist, sb_skill = run_simulation("nearest_with_skill", seed=i)
        e_earn, e_dist, e_skill = run_simulation("equity", seed=i)
        
        baseline_ginis.append(gini(b_earn))
        skill_baseline_ginis.append(gini(sb_earn))
        equity_ginis.append(gini(e_earn))
        
        b_dists.append(b_dist)
        sb_dists.append(sb_dist)
        e_dists.append(e_dist)
        
        b_skills.append(b_skill)
        sb_skills.append(sb_skill)
        e_skills.append(e_skill)
        
    print("Simulation Results (20 seeds):")
    print("==============================")
    print("1. Nearest-Worker Baseline:")
    print(f"   Gini Inequality: {np.mean(baseline_ginis):.3f} ± {np.std(baseline_ginis):.3f}")
    print(f"   Avg Travel Dist: {np.mean(b_dists):.2f} ± {np.std(b_dists):.2f}km")
    print(f"   Skill Match Rate: {np.mean(b_skills):.2f} ± {np.std(b_skills):.2f}")
    
    print("\n2. Nearest-Worker-With-Skill Baseline:")
    print(f"   Gini Inequality: {np.mean(skill_baseline_ginis):.3f} ± {np.std(skill_baseline_ginis):.3f}")
    print(f"   Avg Travel Dist: {np.mean(sb_dists):.2f} ± {np.std(sb_dists):.2f}km")
    print(f"   Skill Match Rate: {np.mean(sb_skills):.2f} ± {np.std(sb_skills):.2f}")
    
    print("\n3. Sahakar Sathi Real Matcher (Equity + Skills + Logistics):")
    print(f"   Gini Inequality: {np.mean(equity_ginis):.3f} ± {np.std(equity_ginis):.3f}")
    print(f"   Avg Travel Dist: {np.mean(e_dists):.2f} ± {np.std(e_dists):.2f}km")
    print(f"   Skill Match Rate: {np.mean(e_skills):.2f} ± {np.std(e_skills):.2f}")
    
    plt.figure(figsize=(10,6))
    plt.plot(np.sort(run_simulation("nearest", seed=42)[0]), label="Nearest-Worker", marker="o", linestyle=":")
    plt.plot(np.sort(run_simulation("nearest_with_skill", seed=42)[0]), label="Nearest-with-Skill", marker="^", linestyle="--")
    plt.plot(np.sort(run_simulation("equity", seed=42)[0]), label="Real Matcher (Sahakar Sathi)", marker="s", linewidth=2)
    plt.title("Earnings Distribution Comparison")
    plt.xlabel("Worker Rank (Poorest to Richest)")
    plt.ylabel("Total Earnings")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig("docs/equity_simulation_chart.png")

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    generate_chart()
