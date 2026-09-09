"""
ServiceRequest business logic layer.

Handles validation, DB queries, status transitions, and response enrichment.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.schemas.service_request import (
    ServiceRequestCreateRequest,
    ServiceRequestResponse,
)
from app.services.cooperative import ensure_demo_cooperative


def build_service_request_response(req: ServiceRequest) -> ServiceRequestResponse:
    """
    Enrich ServiceRequest record with user, service, and cooperative details.
    """
    cust = req.customer
    svc = req.service
    coop = req.cooperative

    return ServiceRequestResponse(
        id=req.id,
        customer_id=req.customer_id,
        customer_name=cust.name if cust else "Unknown Customer",
        customer_email=cust.email if cust else "unknown",
        customer_phone=cust.phone if cust else None,
        service_id=req.service_id,
        service_name=svc.name if svc else "Unknown Service",
        service_category=svc.category if svc else "General",
        cooperative_id=req.cooperative_id,
        cooperative_name=coop.name if coop else None,
        description=req.description,
        location=req.location,
        latitude=req.latitude,
        longitude=req.longitude,
        preferred_date=req.preferred_date,
        preferred_time=req.preferred_time,
        image_url=req.image_url,
        status=req.status,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


def create_service_request(
    db: Session,
    customer_id: int,
    data: ServiceRequestCreateRequest,
) -> ServiceRequest:
    """
    Create a new service request for *customer_id*.

    :raises ValueError: if service does not exist or is inactive.
    """
    service = db.query(Service).filter(Service.id == data.service_id).first()
    if not service:
        raise ValueError("Selected service does not exist")
    if not service.is_active:
        raise ValueError("Selected service is currently inactive")

    # Get or ensure primary cooperative
    coop = ensure_demo_cooperative(db)

    request = ServiceRequest(
        customer_id=customer_id,
        service_id=data.service_id,
        cooperative_id=coop.id,
        description=data.description,
        location=data.location,
        latitude=data.latitude,
        longitude=data.longitude,
        preferred_date=data.preferred_date,
        preferred_time=data.preferred_time,
        status=RequestStatus.PENDING,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_customer_requests(db: Session, customer_id: int) -> List[ServiceRequest]:
    """Return all service requests owned by *customer_id*, newest first."""
    return (
        db.query(ServiceRequest)
        .filter(ServiceRequest.customer_id == customer_id)
        .order_by(ServiceRequest.created_at.desc())
        .all()
    )


def get_request_by_id_for_customer(
    db: Session,
    request_id: int,
    customer_id: int,
) -> Optional[ServiceRequest]:
    """
    Return a request by primary key ONLY if owned by *customer_id*.
    Returns None if the request does not exist OR is owned by another customer.
    """
    return (
        db.query(ServiceRequest)
        .filter(ServiceRequest.id == request_id, ServiceRequest.customer_id == customer_id)
        .first()
    )


def cancel_service_request(
    db: Session,
    request_id: int,
    customer_id: int,
) -> ServiceRequest:
    """
    Cancel a pending request owned by *customer_id*.

    :raises ValueError: if request not found, not owned, or status is not PENDING.
    """
    req = get_request_by_id_for_customer(db, request_id, customer_id)
    if not req:
        raise ValueError("Service request not found")

    if req.status != RequestStatus.PENDING:
        raise ValueError(f"Cannot cancel a request with status '{req.status.value}'")

    req.status = RequestStatus.CANCELLED
    db.commit()
    db.refresh(req)
    return req


def get_all_cooperative_requests_for_admin(db: Session) -> List[ServiceRequest]:
    """Return all service requests for admin management, newest first."""
    return db.query(ServiceRequest).order_by(ServiceRequest.created_at.desc()).all()
