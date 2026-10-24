import os
import sys

# Ensure environment and paths are initialized before imports
os.environ.setdefault("SECRET_KEY", "dev-secret-key-for-simulations")
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if "." not in sys.path:
    sys.path.append(".")

import argparse
import math
import random
import numpy as np
import matplotlib.pyplot as plt

from app.ml.predictor import predict_accept_batch
from app.services.matching.scorer import (
    WEIGHT_SKILL, WEIGHT_LOCATION, WEIGHT_AVAILABILITY,
    WEIGHT_RATING, WEIGHT_EXPERIENCE, WEIGHT_BIO_ECONOMIC
)


def gini(incomes):
    incomes = np.sort(incomes)
    n = len(incomes)
    index = np.arange(1, n + 1)
    if np.sum(incomes) == 0:
        return 0.0
    return float((np.sum((2 * index - n - 1) * incomes)) / (n * np.sum(incomes)))


def dist(c1, c2):
    return math.hypot(c1[0] - c2[0], c1[1] - c2[1])


def bootstrap_ci(diffs, n_boot=10000, ci=95, rng=None):
    if rng is None:
        rng = np.random.default_rng(0)
    diffs = np.array(diffs, dtype=np.float64)
    means = [rng.choice(diffs, size=len(diffs), replace=True).mean() for _ in range(n_boot)]
    lo = np.percentile(means, (100 - ci) / 2)
    hi = np.percentile(means, 100 - (100 - ci) / 2)
    return float(lo), float(hi)


# ---------------------------------------------------------------------------
# Baseline Simulation (Deterministic without offer rejection)
# ---------------------------------------------------------------------------
def run_simulation(strategy="equity", num_jobs=200, num_workers=7, seed=42):
    random.seed(seed)
    np.random.seed(seed)

    worker_earnings = np.zeros(num_workers)
    worker_locs = [(random.uniform(0, 10), random.uniform(0, 10)) for _ in range(num_workers)]
    worker_skills = [set(random.sample(range(10), random.randint(2, 4))) for _ in range(num_workers)]
    worker_ratings = [random.uniform(1.0, 5.0) for _ in range(num_workers)]
    worker_exp = [random.randint(1, 10) for _ in range(num_workers)]

    total_travel = 0
    total_skill_match = 0

    for job_id in range(num_jobs):
        job_value = random.randint(300, 800)
        job_loc = (random.uniform(0, 10), random.uniform(0, 10))
        job_skill = random.randint(0, 9)

        dists = [dist(loc, job_loc) for loc in worker_locs]
        available = list(range(num_workers))

        if strategy == "nearest":
            chosen = min(available, key=lambda w: dists[w])
        elif strategy == "nearest_with_skill":
            skilled = [w for w in available if job_skill in worker_skills[w]]
            if not skilled:
                skilled = available
            chosen = min(skilled, key=lambda w: dists[w])
        else:  # "equity"
            max_earn = max(worker_earnings) if max(worker_earnings) > 0 else 1.0
            scores = []
            max_dist = 14.14

            for w in available:
                skill_score = 100.0 if job_skill in worker_skills[w] else 0.0
                d = min(dists[w], max_dist)
                location_score = max(0.0, 100.0 * (1 - d / max_dist))
                equity_score = max(0.0, 100.0 * (1.0 - (worker_earnings[w] / max_earn)))
                rating_score = (worker_ratings[w] / 5.0) * 100.0
                exp_score = min(100.0, (worker_exp[w] / 10.0) * 100.0)
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

            chosen = available[int(np.argmax(scores))]

        worker_earnings[chosen] += job_value
        total_travel += dists[chosen]
        total_skill_match += 1 if job_skill in worker_skills[chosen] else 0

    return worker_earnings, total_travel / num_jobs, total_skill_match / num_jobs


# ---------------------------------------------------------------------------
# Hidden Logistic Rule for Offer Acceptance
# ---------------------------------------------------------------------------
def hidden_rule_acceptance(
    dist_km: float,
    skill_score: float,
    fatigue: float,
    rating: float,
    exp_years: float,
    earnings: float,
    job_val: float,
    intensity: float,
    hour: int,
    past_rate: float,
    rng: np.random.Generator,
    shift: bool = False,
) -> bool:
    """
    Evaluates worker acceptance/rejection using the ground-truth hidden rule.
    """
    if not shift:
        z = (
            0.25
            - 0.15 * (dist_km - 4.0)
            + 0.020 * (skill_score - 80.0)
            - 0.035 * (fatigue - 30.0)
            + 0.50 * (rating - 4.0)
            + 0.040 * (exp_years - 5.0)
            - 0.00015 * (earnings - 2500.0)
            + 0.0030 * (job_val - 500.0)
            - 1.20 * (intensity - 0.65)
            - 0.15 * max(0, hour - 18)
            + 2.00 * (past_rate - 0.75)
            - 0.0050 * ((dist_km - 4.0) * (fatigue - 30.0))
            + float(rng.normal(0.0, 0.5))
        )
    else:
        # Distribution shift: perturb coefficients by +/- 30% and increase noise
        z = (
            0.25 * 0.85
            - (0.15 * 1.30) * (dist_km - 4.0)
            + (0.020 * 0.70) * (skill_score - 80.0)
            - (0.035 * 1.30) * (fatigue - 30.0)
            + (0.50 * 0.70) * (rating - 4.0)
            + (0.040 * 1.30) * (exp_years - 5.0)
            - (0.00015 * 1.30) * (earnings - 2500.0)
            + (0.0030 * 0.70) * (job_val - 500.0)
            - (1.20 * 1.30) * (intensity - 0.65)
            - (0.15 * 1.30) * max(0, hour - 18)
            + (2.00 * 0.70) * (past_rate - 0.75)
            - (0.0050 * 1.30) * ((dist_km - 4.0) * (fatigue - 30.0))
            + float(rng.normal(0.0, 0.75))
        )
    prob = 1.0 / (1.0 + np.exp(-z))
    return bool(rng.random() < prob)


# ---------------------------------------------------------------------------
# Phase 4: Simulation with Worker Offer Acceptance and ML Tie-Break
# ---------------------------------------------------------------------------
def run_simulation_with_offers(
    strategy: str = "equity",
    num_jobs: int = 200,
    num_workers: int = 30,
    seed: int = 42,
    shift: bool = False,
):
    """
    Simulates dispatched offers with sequential offer escalation on worker decline.
    strategy: 'equity' (Rule-only) or 'ml_tiebreak' (Matcher + ML Tie-Break)
    """
    random.seed(seed)
    np.random.seed(seed)
    accept_rng = np.random.default_rng(seed + 10000)

    worker_earnings = np.zeros(num_workers)
    worker_fatigue = np.zeros(num_workers)
    worker_locs = [(random.uniform(0, 10), random.uniform(0, 10)) for _ in range(num_workers)]
    worker_skills = [set(random.sample(range(10), random.randint(2, 4))) for _ in range(num_workers)]
    worker_ratings = [random.uniform(3.0, 5.0) for _ in range(num_workers)]
    worker_exp = [random.randint(1, 10) for _ in range(num_workers)]
    worker_past_accept = [random.uniform(0.60, 0.95) for _ in range(num_workers)]

    total_travel = 0.0
    total_skill_match = 0
    total_offers_made = 0
    first_offer_accepted_count = 0
    completed_jobs = 0

    max_dist = 14.14

    for job_id in range(num_jobs):
        job_value = random.randint(300, 800)
        job_loc = (random.uniform(0, 10), random.uniform(0, 10))
        job_skill = random.randint(0, 9)
        job_intensity = random.choice([0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85])
        job_hour = random.randint(6, 22)

        # Decay fatigue slightly between jobs (recovery)
        worker_fatigue = worker_fatigue * 0.98

        dists = [dist(loc, job_loc) for loc in worker_locs]

        # Enforce fatigue cap: exclude workers above 80% threshold
        available = [w for w in range(num_workers) if worker_fatigue[w] <= 80.0]
        if not available:
            available = list(range(num_workers))

        max_earn = max(worker_earnings) if max(worker_earnings) > 0 else 1.0
        scores = []
        for w in available:
            skill_score = 100.0 if job_skill in worker_skills[w] else 0.0
            d = min(dists[w], max_dist)
            location_score = max(0.0, 100.0 * (1 - d / max_dist))
            equity_score = max(0.0, 100.0 * (1.0 - (worker_earnings[w] / max_earn)))
            rating_score = (worker_ratings[w] / 5.0) * 100.0
            exp_score = min(100.0, (worker_exp[w] / 10.0) * 100.0)
            avail_score = 100.0

            final_score = (
                (skill_score * WEIGHT_SKILL) +
                (location_score * WEIGHT_LOCATION) +
                (equity_score * WEIGHT_BIO_ECONOMIC) +
                (rating_score * WEIGHT_RATING) +
                (exp_score * WEIGHT_EXPERIENCE) +
                (avail_score * WEIGHT_AVAILABILITY)
            )
            scores.append(round(final_score, 1))

        # Rank candidates descending by total deterministic score
        ranked_indices = list(np.argsort(scores)[::-1])
        candidate_workers = [available[idx] for idx in ranked_indices]
        candidate_scores = [scores[idx] for idx in ranked_indices]

        # ML Tie-Break Policy
        if strategy == "ml_tiebreak" and len(candidate_workers) > 1:
            top_score = candidate_scores[0]
            k_limit = min(len(candidate_workers), 3)
            margin = 2.0
            tie_group = [
                i for i in range(k_limit)
                if (top_score - candidate_scores[i]) <= margin
            ]
            if len(tie_group) > 1:
                batch_features = []
                for idx in tie_group:
                    w = candidate_workers[idx]
                    batch_features.append({
                        "distance_km": dists[w],
                        "skill_match_score": 100.0 if job_skill in worker_skills[w] else 0.0,
                        "fatigue_index": worker_fatigue[w],
                        "rating": worker_ratings[w],
                        "experience_years": worker_exp[w],
                        "recent_earnings": worker_earnings[w],
                        "job_value": float(job_value),
                        "job_intensity": float(job_intensity),
                        "hour_of_day": int(job_hour),
                        "past_acceptance_rate": float(worker_past_accept[w]),
                    })
                probs = predict_accept_batch(batch_features)
                tie_candidates = [
                    (candidate_workers[idx], candidate_scores[idx], probs[i] if probs[i] is not None else 0.0)
                    for i, idx in enumerate(tie_group)
                ]
                tie_candidates.sort(key=lambda item: (item[2], item[1]), reverse=True)
                for i, (cw, cs, _) in enumerate(tie_candidates):
                    candidate_workers[tie_group[i]] = cw
                    candidate_scores[tie_group[i]] = cs

        # Sequential offer loop
        job_completed = False
        offers_count = 0
        for offer_pos, w in enumerate(candidate_workers):
            offers_count += 1
            w_skill_score = 100.0 if job_skill in worker_skills[w] else 0.0
            accepted = hidden_rule_acceptance(
                dist_km=dists[w],
                skill_score=w_skill_score,
                fatigue=worker_fatigue[w],
                rating=worker_ratings[w],
                exp_years=worker_exp[w],
                earnings=worker_earnings[w],
                job_val=job_value,
                intensity=job_intensity,
                hour=job_hour,
                past_rate=worker_past_accept[w],
                rng=accept_rng,
                shift=shift,
            )
            if accepted:
                job_completed = True
                if offer_pos == 0:
                    first_offer_accepted_count += 1
                worker_earnings[w] += job_value
                worker_fatigue[w] = min(100.0, worker_fatigue[w] + (job_intensity * 12.0))
                total_travel += dists[w]
                if job_skill in worker_skills[w]:
                    total_skill_match += 1
                completed_jobs += 1
                break

        total_offers_made += offers_count

    first_offer_rate = first_offer_accepted_count / num_jobs
    avg_offers = total_offers_made / num_jobs
    earnings_gini = gini(worker_earnings)
    avg_travel = total_travel / max(1, completed_jobs)
    skill_match_rate = total_skill_match / max(1, completed_jobs)

    return {
        "first_offer_rate": first_offer_rate,
        "avg_offers": avg_offers,
        "gini": earnings_gini,
        "avg_travel": avg_travel,
        "skill_match_rate": skill_match_rate,
        "completed_jobs": completed_jobs,
        "worker_earnings": worker_earnings,
    }


def run_ml_simulation_comparison():
    output_lines = []

    def log(msg=""):
        safe = msg.encode("ascii", errors="backslashreplace").decode("ascii")
        print(safe)
        output_lines.append(msg)

    log("=" * 78)
    log("SAHAKAR SATHI ML MODULE: 100-SEED SIMULATION & TIE-BREAK EVALUATION")
    log("=" * 78)
    log("Experimental Setup:")
    log("  Seeds           : 100 seeds (0 to 99)")
    log("  Workers         : 30 cooperative workers")
    log("  Jobs per Seed   : 200 service requests")
    log("  Tie-Break Policy: Re-order top candidate offers within 2.0 margin (top-3)")
    log("  Acceptance Model: Calibrated HistGradientBoosting Classifier (CV ROC-AUC: 0.9348)")
    log("  Decision Engine : Sequential offer escalation on worker rejection")

    # -----------------------------------------------------------------------
    # Part 1: Standard Evaluation (Normal Environment)
    # -----------------------------------------------------------------------
    log("\n" + "-" * 78)
    log("PART 1: STANDARD ENVIRONMENT (100 Seeds)")
    log("-" * 78)

    rule_first_rates = []
    rule_avg_offers = []
    rule_ginis = []
    rule_travels = []
    rule_skills = []

    ml_first_rates = []
    ml_avg_offers = []
    ml_ginis = []
    ml_travels = []
    ml_skills = []

    diff_first_rates = []
    diff_offers = []
    diff_ginis = []
    diff_travels = []
    diff_skills = []

    for seed in range(100):
        res_rule = run_simulation_with_offers(
            strategy="equity", num_jobs=200, num_workers=30, seed=seed, shift=False
        )
        res_ml = run_simulation_with_offers(
            strategy="ml_tiebreak", num_jobs=200, num_workers=30, seed=seed, shift=False
        )

        rule_first_rates.append(res_rule["first_offer_rate"])
        rule_avg_offers.append(res_rule["avg_offers"])
        rule_ginis.append(res_rule["gini"])
        rule_travels.append(res_rule["avg_travel"])
        rule_skills.append(res_rule["skill_match_rate"])

        ml_first_rates.append(res_ml["first_offer_rate"])
        ml_avg_offers.append(res_ml["avg_offers"])
        ml_ginis.append(res_ml["gini"])
        ml_travels.append(res_ml["avg_travel"])
        ml_skills.append(res_ml["skill_match_rate"])

        diff_first_rates.append(res_ml["first_offer_rate"] - res_rule["first_offer_rate"])
        diff_offers.append(res_ml["avg_offers"] - res_rule["avg_offers"])
        diff_ginis.append(res_ml["gini"] - res_rule["gini"])
        diff_travels.append(res_ml["avg_travel"] - res_rule["avg_travel"])
        diff_skills.append(res_ml["skill_match_rate"] - res_rule["skill_match_rate"])

    # Summary Stats
    log("\n1. Rule-Only Matcher Baseline (30 workers, 200 jobs, 100 seeds):")
    log(f"   First-Offer Acceptance Rate : {np.mean(rule_first_rates)*100:.2f}% +/- {np.std(rule_first_rates)*100:.2f}%")
    log(f"   Average Offers per Job      : {np.mean(rule_avg_offers):.3f} +/- {np.std(rule_avg_offers):.3f}")
    log(f"   Earnings Gini Inequality    : {np.mean(rule_ginis):.4f} +/- {np.std(rule_ginis):.4f}")
    log(f"   Average Travel Distance     : {np.mean(rule_travels):.2f} +/- {np.std(rule_travels):.2f} km")
    log(f"   Skill-Match Rate            : {np.mean(rule_skills)*100:.2f}% +/- {np.std(rule_skills)*100:.2f}%")

    log("\n2. Sahakar Sathi with ML Tie-Break (30 workers, 200 jobs, 100 seeds):")
    log(f"   First-Offer Acceptance Rate : {np.mean(ml_first_rates)*100:.2f}% +/- {np.std(ml_first_rates)*100:.2f}%")
    log(f"   Average Offers per Job      : {np.mean(ml_avg_offers):.3f} +/- {np.std(ml_avg_offers):.3f}")
    log(f"   Earnings Gini Inequality    : {np.mean(ml_ginis):.4f} +/- {np.std(ml_ginis):.4f}")
    log(f"   Average Travel Distance     : {np.mean(ml_travels):.2f} +/- {np.std(ml_travels):.2f} km")
    log(f"   Skill-Match Rate            : {np.mean(ml_skills)*100:.2f}% +/- {np.std(ml_skills)*100:.2f}%")

    # Bootstrap CIs for Differences
    ci_first_lo, ci_first_hi = bootstrap_ci(diff_first_rates, n_boot=10000, ci=95)
    ci_off_lo, ci_off_hi = bootstrap_ci(diff_offers, n_boot=10000, ci=95)
    ci_gini_lo, ci_gini_hi = bootstrap_ci(diff_ginis, n_boot=10000, ci=95)
    ci_dist_lo, ci_dist_hi = bootstrap_ci(diff_travels, n_boot=10000, ci=95)
    ci_skill_lo, ci_skill_hi = bootstrap_ci(diff_skills, n_boot=10000, ci=95)

    log("\n3. Paired Differences (ML Tie-Break - Rule-Only) with 95% Bootstrap CI (10,000 resamples):")
    log(f"   Delta First-Offer Acceptance: mean = {np.mean(diff_first_rates)*100:+.2f}%, 95% CI = [{ci_first_lo*100:+.2f}%, {ci_first_hi*100:+.2f}%]")
    log(f"   Delta Avg Offers per Job    : mean = {np.mean(diff_offers):+.3f}, 95% CI = [{ci_off_lo:+.3f}, {ci_off_hi:+.3f}]")
    log(f"   Delta Earnings Gini         : mean = {np.mean(diff_ginis):+.4f}, 95% CI = [{ci_gini_lo:+.4f}, {ci_gini_hi:+.4f}]")
    log(f"   Delta Travel Distance       : mean = {np.mean(diff_travels):+.2f} km, 95% CI = [{ci_dist_lo:+.2f} km, {ci_dist_hi:+.2f} km]")
    log(f"   Delta Skill-Match Rate      : mean = {np.mean(diff_skills)*100:+.2f}%, 95% CI = [{ci_skill_lo*100:+.2f}%, {ci_skill_hi*100:+.2f}%]")

    # -----------------------------------------------------------------------
    # Part 2: Distribution Shift Test (+/-30% coefficient perturbation + noise)
    # -----------------------------------------------------------------------
    log("\n" + "-" * 78)
    log("PART 2: DISTRIBUTION SHIFT TEST (Coefficients Perturbed +/-30%, Higher Noise)")
    log("        Models evaluated directly WITHOUT retraining")
    log("-" * 78)

    s_rule_first_rates = []
    s_rule_avg_offers = []
    s_rule_ginis = []
    s_rule_travels = []
    s_rule_skills = []

    s_ml_first_rates = []
    s_ml_avg_offers = []
    s_ml_ginis = []
    s_ml_travels = []
    s_ml_skills = []

    s_diff_first_rates = []
    s_diff_offers = []
    s_diff_ginis = []
    s_diff_travels = []
    s_diff_skills = []

    for seed in range(100):
        res_rule_shift = run_simulation_with_offers(
            strategy="equity", num_jobs=200, num_workers=30, seed=seed, shift=True
        )
        res_ml_shift = run_simulation_with_offers(
            strategy="ml_tiebreak", num_jobs=200, num_workers=30, seed=seed, shift=True
        )

        s_rule_first_rates.append(res_rule_shift["first_offer_rate"])
        s_rule_avg_offers.append(res_rule_shift["avg_offers"])
        s_rule_ginis.append(res_rule_shift["gini"])
        s_rule_travels.append(res_rule_shift["avg_travel"])
        s_rule_skills.append(res_rule_shift["skill_match_rate"])

        s_ml_first_rates.append(res_ml_shift["first_offer_rate"])
        s_ml_avg_offers.append(res_ml_shift["avg_offers"])
        s_ml_ginis.append(res_ml_shift["gini"])
        s_ml_travels.append(res_ml_shift["avg_travel"])
        s_ml_skills.append(res_ml_shift["skill_match_rate"])

        s_diff_first_rates.append(res_ml_shift["first_offer_rate"] - res_rule_shift["first_offer_rate"])
        s_diff_offers.append(res_ml_shift["avg_offers"] - res_rule_shift["avg_offers"])
        s_diff_ginis.append(res_ml_shift["gini"] - res_rule_shift["gini"])
        s_diff_travels.append(res_ml_shift["avg_travel"] - res_rule_shift["avg_travel"])
        s_diff_skills.append(res_ml_shift["skill_match_rate"] - res_rule_shift["skill_match_rate"])

    log("\n1. Rule-Only Matcher under Distribution Shift (100 seeds):")
    log(f"   First-Offer Acceptance Rate : {np.mean(s_rule_first_rates)*100:.2f}% +/- {np.std(s_rule_first_rates)*100:.2f}%")
    log(f"   Average Offers per Job      : {np.mean(s_rule_avg_offers):.3f} +/- {np.std(s_rule_avg_offers):.3f}")
    log(f"   Earnings Gini Inequality    : {np.mean(s_rule_ginis):.4f} +/- {np.std(s_rule_ginis):.4f}")
    log(f"   Average Travel Distance     : {np.mean(s_rule_travels):.2f} +/- {np.std(s_rule_travels):.2f} km")
    log(f"   Skill-Match Rate            : {np.mean(s_rule_skills)*100:.2f}% +/- {np.std(s_rule_skills)*100:.2f}%")

    log("\n2. Sahakar Sathi ML Tie-Break under Distribution Shift (100 seeds):")
    log(f"   First-Offer Acceptance Rate : {np.mean(s_ml_first_rates)*100:.2f}% +/- {np.std(s_ml_first_rates)*100:.2f}%")
    log(f"   Average Offers per Job      : {np.mean(s_ml_avg_offers):.3f} +/- {np.std(s_ml_avg_offers):.3f}")
    log(f"   Earnings Gini Inequality    : {np.mean(s_ml_ginis):.4f} +/- {np.std(s_ml_ginis):.4f}")
    log(f"   Average Travel Distance     : {np.mean(s_ml_travels):.2f} +/- {np.std(s_ml_travels):.2f} km")
    log(f"   Skill-Match Rate            : {np.mean(s_ml_skills)*100:.2f}% +/- {np.std(s_ml_skills)*100:.2f}%")

    s_ci_first_lo, s_ci_first_hi = bootstrap_ci(s_diff_first_rates, n_boot=10000, ci=95)
    s_ci_off_lo, s_ci_off_hi = bootstrap_ci(s_diff_offers, n_boot=10000, ci=95)
    s_ci_gini_lo, s_ci_gini_hi = bootstrap_ci(s_diff_ginis, n_boot=10000, ci=95)
    s_ci_dist_lo, s_ci_dist_hi = bootstrap_ci(s_diff_travels, n_boot=10000, ci=95)
    s_ci_skill_lo, s_ci_skill_hi = bootstrap_ci(s_diff_skills, n_boot=10000, ci=95)

    log("\n3. Paired Differences under Distribution Shift (ML Tie-Break - Rule-Only, 10,000 Bootstrap CI):")
    log(f"   Delta First-Offer Acceptance: mean = {np.mean(s_diff_first_rates)*100:+.2f}%, 95% CI = [{s_ci_first_lo*100:+.2f}%, {s_ci_first_hi*100:+.2f}%]")
    log(f"   Delta Avg Offers per Job    : mean = {np.mean(s_diff_offers):+.3f}, 95% CI = [{s_ci_off_lo:+.3f}, {s_ci_off_hi:+.3f}]")
    log(f"   Delta Earnings Gini         : mean = {np.mean(s_diff_ginis):+.4f}, 95% CI = [{s_ci_gini_lo:+.4f}, {s_ci_gini_hi:+.4f}]")
    log(f"   Delta Travel Distance       : mean = {np.mean(s_diff_travels):+.2f} km, 95% CI = [{s_ci_dist_lo:+.2f} km, {s_ci_dist_hi:+.2f} km]")
    log(f"   Delta Skill-Match Rate      : mean = {np.mean(s_diff_skills)*100:+.2f}%, 95% CI = [{s_ci_skill_lo*100:+.2f}%, {s_ci_skill_hi*100:+.2f}%]")

    # Save to docs/ml/simulation_ml.txt
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    docs_ml_dir = os.path.join(repo_root, "docs", "ml")
    os.makedirs(docs_ml_dir, exist_ok=True)
    out_file = os.path.join(docs_ml_dir, "simulation_ml.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")
    log(f"\nSimulation results saved to: {out_file}")


def generate_chart():
    output_lines = []

    def log(msg=""):
        safe_msg = msg.encode("ascii", errors="backslashreplace").decode("ascii")
        print(safe_msg)
        output_lines.append(msg)

    # Configuration 1: 7 workers, 200 jobs, 20 seeds
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

    # Save to docs/simulation_results.txt
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    docs_dir = os.path.join(repo_root, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    res_path = os.path.join(docs_dir, "simulation_results.txt")
    with open(res_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")
    print(f"Results saved to {res_path}")

    try:
        plt.figure(figsize=(10, 6))
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
    parser = argparse.ArgumentParser(description="Simulation Engine")
    parser.add_argument("--legacy-only", action="store_true", help="Run only legacy baseline simulation")
    parser.add_argument("--ml-only", action="store_true", help="Run only ML tie-break simulation")
    args = parser.parse_args()

    if args.legacy_only:
        generate_chart()
    elif args.ml_only:
        run_ml_simulation_comparison()
    else:
        # Run both
        generate_chart()
        run_ml_simulation_comparison()
