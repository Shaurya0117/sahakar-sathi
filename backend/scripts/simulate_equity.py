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

def bootstrap_ci(diffs, n_boot=10000, ci=95, rng=None):
    if rng is None:
        rng = np.random.default_rng(0)
    diffs = np.array(diffs)
    means = [rng.choice(diffs, size=len(diffs), replace=True).mean() for _ in range(n_boot)]
    lo = np.percentile(means, (100 - ci) / 2)
    hi = np.percentile(means, 100 - (100 - ci) / 2)
    return float(lo), float(hi)

def generate_chart():
    output_lines = []
    def log(msg=""):
        safe_msg = msg.encode('ascii', errors='backslashreplace').decode('ascii')
        print(safe_msg)
        output_lines.append(msg)

    # -------------------------------------------------------------
    # Configuration 1: Existing 7 workers, 200 jobs, 20 seeds
    # -------------------------------------------------------------
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
        
    log("Simulation Results (20 seeds):")
    log("==============================")
    log("1. Nearest-Worker Baseline:")
    log(f"   Gini Inequality: {np.mean(baseline_ginis):.3f} +/- {np.std(baseline_ginis):.3f}")
    log(f"   Avg Travel Dist: {np.mean(b_dists):.2f} +/- {np.std(b_dists):.2f}km")
    log(f"   Skill Match Rate: {np.mean(b_skills):.2f} +/- {np.std(b_skills):.2f}")
    
    log("\n2. Nearest-Worker-With-Skill Baseline:")
    log(f"   Gini Inequality: {np.mean(skill_baseline_ginis):.3f} +/- {np.std(skill_baseline_ginis):.3f}")
    log(f"   Avg Travel Dist: {np.mean(sb_dists):.2f} +/- {np.std(sb_dists):.2f}km")
    log(f"   Skill Match Rate: {np.mean(sb_skills):.2f} +/- {np.std(sb_skills):.2f}")
    
    log("\n3. Sahakar Sathi Real Matcher (Equity + Skills + Logistics):")
    log(f"   Gini Inequality: {np.mean(equity_ginis):.3f} +/- {np.std(equity_ginis):.3f}")
    log(f"   Avg Travel Dist: {np.mean(e_dists):.2f} +/- {np.std(e_dists):.2f}km")
    log(f"   Skill Match Rate: {np.mean(e_skills):.2f} +/- {np.std(e_skills):.2f}")
    
    # -------------------------------------------------------------
    # Configuration 2: 30 workers, 200 jobs, 100 seeds (0-99)
    # -------------------------------------------------------------
    log("\n" + "=" * 60)
    log("Simulation Results (100 seeds, 30 workers, 200 jobs):")
    log("============================================================")
    
    c2_sb_ginis = []
    c2_sb_dists = []
    c2_sb_skills = []
    c2_e_ginis = []
    c2_e_dists = []
    c2_e_skills = []

    diff_ginis = []
    diff_dists = []
    diff_skills = []

    for seed in range(100):
        sb_earn, sb_dist, sb_skill = run_simulation("nearest_with_skill", num_jobs=200, num_workers=30, seed=seed)
        e_earn, e_dist, e_skill = run_simulation("equity", num_jobs=200, num_workers=30, seed=seed)

        sb_g = gini(sb_earn)
        e_g = gini(e_earn)

        c2_sb_ginis.append(sb_g)
        c2_sb_dists.append(sb_dist)
        c2_sb_skills.append(sb_skill)

        c2_e_ginis.append(e_g)
        c2_e_dists.append(e_dist)
        c2_e_skills.append(e_skill)

        diff_ginis.append(e_g - sb_g)
        diff_dists.append(e_dist - sb_dist)
        diff_skills.append(e_skill - sb_skill)

    log("1. Nearest-Worker-With-Skill Baseline (30 workers):")
    log(f"   Gini Inequality: {np.mean(c2_sb_ginis):.4f} +/- {np.std(c2_sb_ginis):.4f}")
    log(f"   Avg Travel Dist: {np.mean(c2_sb_dists):.2f} +/- {np.std(c2_sb_dists):.2f}km")
    log(f"   Skill Match Rate: {np.mean(c2_sb_skills):.4f} +/- {np.std(c2_sb_skills):.4f}")

    log("\n2. Sahakar Sathi Real Matcher (30 workers):")
    log(f"   Gini Inequality: {np.mean(c2_e_ginis):.4f} +/- {np.std(c2_e_ginis):.4f}")
    log(f"   Avg Travel Dist: {np.mean(c2_e_dists):.2f} +/- {np.std(c2_e_dists):.2f}km")
    log(f"   Skill Match Rate: {np.mean(c2_e_skills):.4f} +/- {np.std(c2_e_skills):.4f}")

    # Bootstrap CI for per-seed differences (Equity - Nearest_with_skill)
    ci_gini_lo, ci_gini_hi = bootstrap_ci(diff_ginis, n_boot=10000, ci=95)
    ci_dist_lo, ci_dist_hi = bootstrap_ci(diff_dists, n_boot=10000, ci=95)
    ci_skill_lo, ci_skill_hi = bootstrap_ci(diff_skills, n_boot=10000, ci=95)

    log("\n3. Per-Seed Differences (Equity - Nearest_With_Skill) with 95% Bootstrap CI (10,000 resamples):")
    log(f"   Delta Gini Inequality : mean = {np.mean(diff_ginis):+.4f}, 95% CI = [{ci_gini_lo:+.4f}, {ci_gini_hi:+.4f}]")
    log(f"   Delta Travel Distance : mean = {np.mean(diff_dists):+.2f}km, 95% CI = [{ci_dist_lo:+.2f}km, {ci_dist_hi:+.2f}km]")
    log(f"   Delta Skill Match Rate: mean = {np.mean(diff_skills):+.4f}, 95% CI = [{ci_skill_lo:+.4f}, {ci_skill_hi:+.4f}]")

    # Save to docs/simulation_results.txt
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    docs_dir = os.path.join(repo_root, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    res_path = os.path.join(docs_dir, "simulation_results.txt")
    with open(res_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")
    print(f"Results saved to {res_path}")

    # Save figure
    try:
        plt.figure(figsize=(10,6))
        plt.plot(np.sort(run_simulation("nearest", seed=42)[0]), label="Nearest-Worker", marker="o", linestyle=":")
        plt.plot(np.sort(run_simulation("nearest_with_skill", seed=42)[0]), label="Nearest-with-Skill", marker="^", linestyle="--")
        plt.plot(np.sort(run_simulation("equity", seed=42)[0]), label="Real Matcher (Sahakar Sathi)", marker="s", linewidth=2)
        plt.title("Earnings Distribution Comparison")
        plt.xlabel("Worker Rank (Poorest to Richest)")
        plt.ylabel("Total Earnings")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(docs_dir, "equity_simulation_chart.png"))
    except Exception as e:
        print(f"Chart generation note: {e}")

if __name__ == "__main__":
    generate_chart()
