"""
Worker business logic / service layer.

Route handlers call these functions; they do not interact with SQLAlchemy directly.

Key rules enforced here (not just in schema):
    - Workers cannot change verification_status, rating, total_jobs.
    - Duplicate worker profile (same user_id) raises ValueError.
    - Profile completion is calculated server-side.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.schemas.worker import (
    WorkerCreateRequest,
    WorkerResponse,
    WorkerUpdateRequest,
)


# ── Profile completion ─────────────────────────────────────────────────────────

# The set of fields that count towards profile completion.
_COMPLETION_FIELDS = ["profession", "experience_years", "location", "skills", "availability"]


def calculate_profile_completion(worker: Worker) -> int:
    """
    Return an integer 0–100 representing profile completion.

    Rules:
        profession      — non-null and non-empty string
        experience_years — non-null (0 is valid)
        location        — non-null and non-empty string
        skills          — non-null list with at least one entry
        availability    — always set (has a default), so always counts as complete
    """
    filled = 0

    if worker.profession and worker.profession.strip():
        filled += 1

    if worker.experience_years is not None:
        filled += 1

    if worker.location and worker.location.strip():
        filled += 1

    if worker.skills and len(worker.skills) > 0:
        filled += 1

    # availability always has a default — counts as filled
    if worker.availability:
        filled += 1

    total = len(_COMPLETION_FIELDS)
    return int(round(filled / total * 100))


# ── Response builder ───────────────────────────────────────────────────────────

def build_worker_response(worker: Worker) -> WorkerResponse:
    """
    Build a WorkerResponse, enriching the worker data with fields from the
    linked User and computing profile_completion server-side.
    """
    user = worker.user
    return WorkerResponse(
        id=worker.id,
        user_id=worker.user_id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        profession=worker.profession,
        skills=worker.skills or [],
        experience_years=worker.experience_years,
        location=worker.location,
        latitude=worker.latitude,
        longitude=worker.longitude,
        availability=worker.availability,
        availability_description=worker.availability_description,
        verification_status=worker.verification_status,
        rating=worker.rating,
        total_jobs=worker.total_jobs,
        profile_completion=calculate_profile_completion(worker),
    )


# ── CRUD ───────────────────────────────────────────────────────────────────────

def get_worker_by_user_id(db: Session, user_id: int) -> Optional[Worker]:
    """Return the Worker profile for a given user_id, or None."""
    return db.query(Worker).filter(Worker.user_id == user_id).first()


def get_worker_by_id(db: Session, worker_id: int) -> Optional[Worker]:
    """Return a Worker by primary key, or None."""
    return db.query(Worker).filter(Worker.id == worker_id).first()


def get_all_workers(db: Session) -> List[Worker]:
    """Return all worker profiles (used by admin listing)."""
    return db.query(Worker).all()


def create_worker_profile(db: Session, user_id: int, data: WorkerCreateRequest) -> Worker:
    """
    Create a new worker profile for *user_id*.

    :raises ValueError: if a profile already exists for this user.
    """
    if get_worker_by_user_id(db, user_id):
        raise ValueError("Worker profile already exists for this user")

    worker = Worker(
        user_id=user_id,
        profession=data.profession,
        skills=data.skills,
        experience_years=data.experience_years,
        location=data.location,
        latitude=data.latitude,
        longitude=data.longitude,
        availability=data.availability,
        availability_description=data.availability_description,
        # Protected defaults — NOT set from request
        verification_status=VerificationStatus.PENDING,
        rating=0.0,
        total_jobs=0,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


def update_worker_profile(db: Session, worker: Worker, data: WorkerUpdateRequest) -> Worker:
    """
    Apply partial updates to a worker profile.

    Only fields provided in WorkerUpdateRequest are changed.
    Protected fields (verification_status, rating, total_jobs) are never touched.
    """
    if data.profession is not None:
        worker.profession = data.profession
    if data.skills is not None:
        worker.skills = data.skills
    if data.experience_years is not None:
        worker.experience_years = data.experience_years
    if data.location is not None:
        worker.location = data.location
    if data.latitude is not None:
        worker.latitude = data.latitude
    if data.longitude is not None:
        worker.longitude = data.longitude
    if data.availability is not None:
        worker.availability = data.availability
    if data.availability_description is not None:
        worker.availability_description = data.availability_description

    db.commit()
    db.refresh(worker)
    return worker


# ── Admin-only: verification ───────────────────────────────────────────────────

def update_verification_status(
    db: Session,
    worker: Worker,
    new_status: VerificationStatus,
) -> Worker:
    """
    Change verification_status — callable only from the admin route.

    Workers are blocked at the route/dependency level before this is called.
    """
    worker.verification_status = new_status
    db.commit()
    db.refresh(worker)
    return worker
