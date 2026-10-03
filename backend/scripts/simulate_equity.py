import numpy as np
import matplotlib.pyplot as plt
import random
import math

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
    
    total_travel = 0
    total_skill_match = 0
    
    for job_id in range(num_jobs):
        job_value = random.randint(300, 800)
        job_loc = (random.uniform(0, 10), random.uniform(0, 10))
        job_skill = random.randint(0, 9)
        
        # Calculate distances for all workers
        dists = [dist(loc, job_loc) for loc in worker_locs]
        
        # Available workers (assume all are available for simplicity)
        available = list(range(num_workers))
        
        if strategy == "nearest":
            # Pick the worker with minimum distance
            chosen = min(available, key=lambda w: dists[w])
        else:
            # Equity matcher: score based on real weights (e.g. 82% equity, 18% distance penalty)
            # Normalizing earnings so max is 1.0 (to avoid massive penalty or 0)
            max_earn = max(worker_earnings) if max(worker_earnings) > 0 else 1.0
            scores = []
            for w in available:
                # the scoring function prioritizes those with fewer earnings
                # lower earnings = higher score
                equity_score = 1.0 - (worker_earnings[w] / max_earn) 
                
                # smaller distance = higher score
                max_dist = 14.14 # sqrt(10^2 + 10^2)
                dist_score = 1.0 - (dists[w] / max_dist)
                
                # skill match = +20% bump if they have it
                skill_bump = 0.2 if job_skill in worker_skills[w] else 0.0
                
                final_score = (equity_score * 0.82) + (dist_score * 0.18) + skill_bump
                scores.append(final_score)
                
            chosen = available[np.argmax(scores)]
            
        worker_earnings[chosen] += job_value
        total_travel += dists[chosen]
        total_skill_match += 1 if job_skill in worker_skills[chosen] else 0
        
    return worker_earnings, total_travel / num_jobs, total_skill_match / num_jobs

def generate_chart():
    baseline_ginis = []
    equity_ginis = []
    b_dists = []
    e_dists = []
    b_skills = []
    e_skills = []
    
    for i in range(20):
        b_earn, b_dist, b_skill = run_simulation("nearest", seed=i)
        e_earn, e_dist, e_skill = run_simulation("equity", seed=i)
        
        baseline_ginis.append(gini(b_earn))
        equity_ginis.append(gini(e_earn))
        b_dists.append(b_dist)
        e_dists.append(e_dist)
        b_skills.append(b_skill)
        e_skills.append(e_skill)
        
    print("nearest-worker vs equity matcher (20 seeds):")
    print(f"Gini: {np.mean(baseline_ginis):.3f}±{np.std(baseline_ginis):.3f} vs {np.mean(equity_ginis):.3f}±{np.std(equity_ginis):.3f}")
    print(f"Avg Travel Dist: {np.mean(b_dists):.2f}±{np.std(b_dists):.2f}km vs {np.mean(e_dists):.2f}±{np.std(e_dists):.2f}km")
    print(f"Skill Match Rate: {np.mean(b_skills):.2f}±{np.std(b_skills):.2f} vs {np.mean(e_skills):.2f}±{np.std(e_skills):.2f}")
    
    plt.figure(figsize=(10,6))
    plt.plot(np.sort(run_simulation("nearest", seed=42)[0]), label="Nearest-Worker", marker="o")
    plt.plot(np.sort(run_simulation("equity", seed=42)[0]), label="Equity", marker="s")
    plt.title("Earnings Distribution (Synthetic Data)")
    plt.xlabel("Worker Rank")
    plt.ylabel("Earnings")
    plt.legend()
    plt.savefig("C:/Users/shaur/Downloads/SIH26-main/SIH26-main/docs/equity_simulation_chart.png")

if __name__ == "__main__":
    import os
    os.makedirs("C:/Users/shaur/Downloads/SIH26-main/SIH26-main/docs", exist_ok=True)
    generate_chart()

