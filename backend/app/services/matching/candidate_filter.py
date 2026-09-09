"""
Candidate Filtering for Worker Matching.

Eliminates ineligible workers based on strict cooperative criteria:
1. Worker must belong to the request's cooperative.
2. Worker verification_status == VERIFIED.
3. Worker availability == AVAILABLE.
4. Worker profession or skills must have basic relevance to the requested service.
"""
import re
from typing import List

from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.service_request import ServiceRequest
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker


def normalize_text(text: str) -> str:
    """Lowercase and strip non-alphanumeric characters for keyword matching."""
    if not text:
        return ""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def is_profession_or_skill_relevant(service: Service, worker: Worker) -> bool:
    """
    Check if worker's profession or skills share basic relevance with the requested service.
    """
    service_text = normalize_text(f"{service.name} {service.category}")
    prof_text = normalize_text(worker.profession or "")
    skills_text = normalize_text(" ".join(worker.skills or []))

    # Keyword mappings for common service domains
    domain_keywords = {
        "electric": ["electric", "wiring", "fan", "switch", "mcb", "light", "socket"],
        "plumb": ["plumb", "pipe", "leak", "tap", "drain", "bath", "sink"],
        "clean": ["clean", "sanitiz", "wash", "sweep", "dust", "mop"],
        "carpent": ["carpent", "wood", "furniture", "door", "window", "cabinet"],
        "paint": ["paint", "wall", "color", "damp", "texture"],
        "ac": ["ac", "air condition", "cool", "refrigerat", "gas", "compressor"],
    }

    # Check matching keywords between service and worker
    for key, keywords in domain_keywords.items():
        if any(kw in service_text for kw in keywords):
            if any(kw in prof_text or kw in skills_text for kw in keywords):
                return True

    # Generic substring match fallback
    service_words = [w for w in service_text.split() if len(w) > 3]
    for w in service_words:
        if w in prof_text or w in skills_text:
            return True

    # Direct containment
    if prof_text and (prof_text in service_text or service_text in prof_text):
        return True

    return False


def filter_eligible_candidates(db: Session, request: ServiceRequest) -> List[Worker]:
    """
    Return all eligible worker candidates for *request*.

    Filters:
    - Same cooperative ID (or default coop)
    - VERIFIED status
    - AVAILABLE status
    - Relevant profession or skills
    """
    query = db.query(Worker).filter(
        Worker.verification_status == VerificationStatus.VERIFIED,
        Worker.availability == AvailabilityStatus.AVAILABLE,
    )

    # Filter by cooperative membership
    if request.cooperative_id:
        query = query.filter(
            (Worker.cooperative_id == request.cooperative_id) | (Worker.cooperative_id.is_(None))
        )

    all_verified_available = query.all()

    # Filter by skill / profession relevance
    service = request.service
    if not service:
        service = db.query(Service).filter(Service.id == request.service_id).first()

    if not service:
        return all_verified_available

    eligible = [w for w in all_verified_available if is_profession_or_skill_relevant(service, w)]
    return eligible
