"""
Matching Engine Orchestrator.

Combines candidate filtering, scoring, explainability, equity graph, and ranking.

Patent Feature: Integrates the Cooperative Workload Equity Graph for
multi-dimensional fairness-aware worker matching.
"""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.user import User
from app.schemas.matching import (
    EquityBreakdown,
    EquityDimensionContributions,
    RequestMatchingResponse,
    ScoreBreakdown,
    WorkerRecommendation,
)
from app.services.matching.candidate_filter import filter_eligible_candidates
from app.services.matching.equity_graph import calculate_equity_score
from app.services.matching.explain import generate_match_explanation
from app.services.matching.scorer import (
    calculate_availability_score,
    calculate_experience_score,
    calculate_bio_economic_metrics,
    calculate_location_score,
    calculate_rating_score,
    calculate_skill_score,
    calculate_total_score,
)


def get_matching_recommendations(
    db: Session,
    request_id: int,
) -> RequestMatchingResponse:
    """
    Generate explainable worker recommendations for service request *request_id*.

    Returns RequestMatchingResponse with candidate_count and ranked worker recommendations.
    Now includes Patent Feature: Cooperative Workload Equity Graph — multi-dimensional
    fairness breakdown for each candidate.

    Raises HTTPException 404 if request not found.
    """
    request = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="Service request not found.")

    service = request.service
    if not service:
        service = db.query(Service).filter(Service.id == request.service_id).first()

    service_name = service.name if service else "General Service"
    service_category = service.category if service else "Household"

    # Step 1: Candidate Discovery & Eligibility Filtering
    candidates = filter_eligible_candidates(db, request)

    recommendations: List[WorkerRecommendation] = []

    # Step 2, 3, 4: Score, Equity Graph, & Explain Each Candidate
    for worker in candidates:
        user = db.query(User).filter(User.id == worker.user_id).first()
        worker_name = user.name if user else f"Worker #{worker.id}"

        skill_score = calculate_skill_score(service, worker)
        location_score = calculate_location_score(
            request.location,
            worker.location,
            request_lat=getattr(request, "latitude", None),
            request_lon=getattr(request, "longitude", None),
            worker_lat=getattr(worker, "latitude", None),
            worker_lon=getattr(worker, "longitude", None),
        )
        availability_score = calculate_availability_score(worker)
        rating_score = calculate_rating_score(worker)
        experience_score = calculate_experience_score(worker)
        bio_metrics = calculate_bio_economic_metrics(worker)

        # Patent Feature: Cooperative Workload Equity Graph
        equity_data = calculate_equity_score(db, worker)

        # Safety floor: exclude fatigued workers (from either legacy or equity check)
        if bio_metrics.get("is_fatigued") or equity_data.get("is_fatigued"):
            continue

        # Build equity breakdown for response
        equity_contributions = equity_data.get("dimension_contributions", {})
        equity_breakdown = EquityBreakdown(
            income_parity=equity_data["income_parity"],
            geographic_burden=equity_data["geographic_burden"],
            skill_utilization=equity_data["skill_utilization"],
            temporal_fairness=equity_data["temporal_fairness"],
            fatigue_capacity=equity_data["fatigue_capacity"],
            composite_equity_score=equity_data["composite_equity_score"],
            is_fatigued=equity_data["is_fatigued"],
            dimension_contributions=EquityDimensionContributions(**equity_contributions) if equity_contributions else None,
        )

        breakdown_dict = {
            "skill_match": skill_score,
            "location": location_score,
            "availability": availability_score,
            "rating": rating_score,
            "experience": experience_score,
            "bio_economic_score": bio_metrics["bio_economic_score"],
            "fatigue_index": bio_metrics["fatigue_index"],
            "economic_deficit": bio_metrics["economic_deficit"],
            "equity_score": equity_data["composite_equity_score"],
        }

        total_score = calculate_total_score(breakdown_dict)
        reasons = generate_match_explanation(breakdown_dict, service, worker, request.location)

        # Add equity-specific explanation
        equity_composite = equity_data["composite_equity_score"]
        if equity_composite >= 75:
            reasons.append(f"High cooperative equity priority (Equity Score: {equity_composite}/100)")
        elif equity_composite >= 50:
            reasons.append(f"Fair cooperative equity standing (Equity Score: {equity_composite}/100)")

        # Retrieve trust score if available
        trust_score_val = getattr(worker, 'trust_score', None)

        recommendations.append(
            WorkerRecommendation(
                worker_id=worker.id,
                worker_name=worker_name,
                profession=worker.profession,
                verification_status=worker.verification_status.value if hasattr(worker.verification_status, 'value') else str(worker.verification_status),
                rating=worker.rating or 0.0,
                experience_years=worker.experience_years or 0,
                location=worker.location,
                total_jobs=worker.total_jobs or 0,
                score=total_score,
                breakdown=ScoreBreakdown(**breakdown_dict, equity=equity_breakdown),
                reasons=reasons,
                trust_score=trust_score_val,
            )
        )

    # Step 5: Rank candidates descending by total score
    recommendations.sort(key=lambda r: r.score, reverse=True)

    return RequestMatchingResponse(
        request_id=request.id,
        service_name=service_name,
        service_category=service_category,
        request_location=request.location,
        candidate_count=len(recommendations),
        recommendations=recommendations,
    )

