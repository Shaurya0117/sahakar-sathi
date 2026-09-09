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

    # 6. Bio-Economic Fatigue Routing reason
    bio_score = breakdown.get("bio_economic_score", 0)
    fatigue = breakdown.get("fatigue_index", 0)
    deficit = breakdown.get("economic_deficit", 0)
    
    if bio_score >= 80:
        reasons.append(f"Highly optimized bio-economic match (Income deficit: {deficit}%, Fatigue: {fatigue}%)")
    elif bio_score >= 50:
        reasons.append(f"Fair bio-economic routing priority (Fatigue Index: {fatigue}%)")

    return reasons
