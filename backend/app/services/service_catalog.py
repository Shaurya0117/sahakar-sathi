"""
Service catalog business logic layer.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.service import Service
from app.schemas.service import ServiceCreateRequest

DEFAULT_SERVICES = [
    {
        "name": "Women's Salon - Haircut & Styling",
        "category": "Beauty & Spa",
        "description": "Premium haircut, wash, and styling at home.",
        "price": 599.0, "duration_minutes": 45, "icon": "✂️", "image_url": "https://images.unsplash.com/photo-1562322140-8baeececf3df?auto=format&fit=crop&q=80&w=400", "rating": 4.8, "reviews_count": 120,
    },
    {
        "name": "Women's Spa & Massage",
        "category": "Beauty & Spa",
        "description": "Relaxing full body spa session by professional therapists.",
        "price": 1499.0, "duration_minutes": 90, "icon": "💆‍♀️", "image_url": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?auto=format&fit=crop&q=80&w=400", "rating": 4.9, "reviews_count": 85,
    },
    {
        "name": "Men's Haircut & Grooming",
        "category": "Men's Salon",
        "description": "Professional men's haircut and beard styling.",
        "price": 299.0, "duration_minutes": 30, "icon": "💈", "image_url": "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&q=80&w=400", "rating": 4.7, "reviews_count": 230,
    },
    {
        "name": "AC Servicing & Repair",
        "category": "Repairs",
        "description": "Comprehensive AC cleaning and check-up.",
        "price": 499.0, "duration_minutes": 60, "icon": "❄️", "image_url": "https://images.unsplash.com/photo-1599839619722-39751411ea63?auto=format&fit=crop&q=80&w=400", "rating": 4.6, "reviews_count": 540,
    },
    {
        "name": "Washing Machine Repair",
        "category": "Repairs",
        "description": "Diagnosis and repair for fully/semi automatic machines.",
        "price": 399.0, "duration_minutes": 45, "icon": "🧺", "image_url": "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?auto=format&fit=crop&q=80&w=400", "rating": 4.5, "reviews_count": 112,
    },
    {
        "name": "Full Home Deep Cleaning",
        "category": "Cleaning",
        "description": "Intense deep cleaning for floors, bathrooms, and kitchen.",
        "price": 2499.0, "duration_minutes": 240, "icon": "🧹", "image_url": "https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&q=80&w=400", "rating": 4.9, "reviews_count": 76,
    },
    {
        "name": "Bathroom Deep Cleaning",
        "category": "Cleaning",
        "description": "Stain removal and sanitization of bathroom fixtures.",
        "price": 399.0, "duration_minutes": 60, "icon": "🛁", "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&q=80&w=400", "rating": 4.8, "reviews_count": 310,
    },
    {
        "name": "Sofa & Carpet Cleaning",
        "category": "Cleaning",
        "description": "Shampooing and vacuuming of sofas (up to 5 seats).",
        "price": 799.0, "duration_minutes": 90, "icon": "🛋️", "image_url": "https://images.unsplash.com/photo-1527515637-edbc2417730e?auto=format&fit=crop&q=80&w=400", "rating": 4.7, "reviews_count": 145,
    },
    {
        "name": "Plumbing Leak Fixes",
        "category": "Plumbing",
        "description": "Fix leaks, drips, or blockages in pipes.",
        "price": 199.0, "duration_minutes": 30, "icon": "🔧", "image_url": "https://images.unsplash.com/photo-1607472586893-edb57cb5b28b?auto=format&fit=crop&q=80&w=400", "rating": 4.5, "reviews_count": 420,
    },
    {
        "name": "Electrical Switch/Socket Repair",
        "category": "Electrician",
        "description": "Fix or replace faulty switches and sockets.",
        "price": 149.0, "duration_minutes": 30, "icon": "⚡", "image_url": "https://images.unsplash.com/photo-1580216641603-9eb17601d322?auto=format&fit=crop&q=80&w=400", "rating": 4.6, "reviews_count": 350,
    },
]


def get_all_services(db: Session, active_only: bool = True) -> List[Service]:
    """Return all services in the catalog."""
    query = db.query(Service)
    if active_only:
        query = query.filter(Service.is_active.is_(True))
    return query.order_by(Service.name.asc()).all()


def get_service_by_id(db: Session, service_id: int) -> Optional[Service]:
    """Return a service by primary key."""
    return db.query(Service).filter(Service.id == service_id).first()


def create_service(db: Session, data: ServiceCreateRequest) -> Service:
    """Create a new catalog service."""
    existing = db.query(Service).filter(Service.name == data.name).first()
    if existing:
        raise ValueError(f"Service '{data.name}' already exists in catalog.")

    service = Service(
        name=data.name,
        category=data.category,
        description=data.description,
        price=data.price,
        duration_minutes=data.duration_minutes,
        image_url=data.image_url,
        icon=data.icon,
        rating=data.rating,
        reviews_count=data.reviews_count,
        is_active=data.is_active,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def ensure_seed_services(db: Session) -> List[Service]:
    """
    Seed standard default services into the catalog if absent.
    """
    services = []
    for item in DEFAULT_SERVICES:
        existing = db.query(Service).filter(Service.name == item["name"]).first()
        if not existing:
            svc = Service(
                name=item["name"],
                category=item["category"],
                description=item["description"],
                price=item.get("price", 0.0),
                duration_minutes=item.get("duration_minutes", 60),
                icon=item.get("icon"),
                image_url=item.get("image_url"),
                rating=item.get("rating", 5.0),
                reviews_count=item.get("reviews_count", 0),
                is_active=True,
            )
            db.add(svc)
            services.append(svc)
        else:
            services.append(existing)

    db.commit()
    return get_all_services(db)
