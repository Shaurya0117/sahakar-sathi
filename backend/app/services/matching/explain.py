"""
Explanation Generator for Worker Matching Recommendations.

Translates component score breakdown into transparent, human-readable bullet points.
"""
from typing import List

from app.models.service import Service
from app.models.worker import Worker


def generate_match_explanation(
    breakdown: dict,
    service: Service,
    worker: Worker,
    request_location: str,
) -> List[str]:
    """
    Generate bullet points explaining why *worker* was recommended for *service*.
    Directly reflects component score values.
    """
    reasons = []

    # 1. Skill Match reason
    skill_score = breakdown.get("skill_match", 0)
    if skill_score >= 85:
        reasons.append(f"Strong {worker.profession or service.name} skill match")
    elif skill_score >= 65:
        reasons.append(f"Relevant qualifications for {service.name}")

    # 2. Location reason
    loc_score = breakdown.get("location", 0)
    if loc_score >= 85:
        reasons.append("High location compatibility (same service area)")
    elif loc_score >= 70:
        reasons.append("Located in neighboring service region")

    # 3. Availability reason
    avail_score = breakdown.get("availability", 0)
    if avail_score >= 100:
        reasons.append("Available for service allocation")

    # 4. Rating reason
    if worker.rating and worker.rating >= 4.5:
        reasons.append(f"Highly rated by cooperative customers ({worker.rating:.1f} ★)")
    elif worker.rating and worker.rating >= 4.0:
        reasons.append(f"Solid customer rating ({worker.rating:.1f} ★)")
    elif not worker.rating or worker.rating == 0:
        reasons.append("New worker (neutral rating entry)")

    # 5. Experience reason
    exp_years = worker.experience_years or 0
    if exp_years >= 5:
        reasons.append(f"Experienced professional ({exp_years} years in field)")
    elif exp_years >= 2:
        reasons.append(f"Good experience level ({exp_years} years)")

    # 6. Workload Fairness reason
    fairness_score = breakdown.get("workload_fairness", breakdown.get("fairness", 0))
    if fairness_score >= 85:
        reasons.append("Low current workload (promotes fair cooperative work distribution)")
    elif fairness_score >= 60:
        reasons.append("Balanced current workload")

    return reasons
