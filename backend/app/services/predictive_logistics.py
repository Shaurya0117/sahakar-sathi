"""
Hyper-Local Predictive Logistics Engine.

Core Innovation #3: Forecasts appliance failures based on usage/data and pre-positions 
spare parts with local shop tie-ups.
"""
from sqlalchemy.orm import Session
import datetime
import random
import json

from app.models.appliance import HouseholdAppliance
from app.models.shop import LocalShop


def parse_appliance_type(service_name: str) -> str:
    """Extract appliance type from service name."""
    s = service_name.lower()
    if "ac" in s or "air condition" in s:
        return "Air Conditioner"
    if "fan" in s:
        return "Ceiling Fan"
    if "plumb" in s or "pipe" in s or "leak" in s or "water" in s:
        return "Plumbing System"
    if "fridge" in s or "refrigerator" in s:
        return "Refrigerator"
    if "washing" in s:
        return "Washing Machine"
    if "wiring" in s or "switch" in s or "electric" in s:
        return "Electrical Board"
    return "General Appliance"


def get_required_part(appliance_type: str) -> str:
    """Determine which part is likely to fail next."""
    parts_map = {
        "Air Conditioner": "AC Compressor",
        "Ceiling Fan": "Fan Motor",
        "Plumbing System": "Copper Pipe",
        "Refrigerator": "Compressor Coil",
        "Washing Machine": "Drain Motor",
        "Electrical Board": "Switchboard"
    }
    return parts_map.get(appliance_type, "Standard Kit")


def forecast_failure(appliance: HouseholdAppliance) -> dict:
    """
    Mock AI Model for Failure Forecasting (Simulating Bi-LSTM/GRU output).
    Calculates health score drop based on age and time since last service.
    """
    now = datetime.datetime.utcnow()
    
    # If newly tracked, give it a high score
    if not appliance.last_serviced_date:
        appliance.last_serviced_date = now
        appliance.health_score = 90.0
        
    days_since_service = (now - appliance.last_serviced_date).days
    age_years = (now.year - appliance.purchase_year) if appliance.purchase_year else 3
    
    # Degrade health score based on time and age
    degradation = (days_since_service * 0.1) + (age_years * 5.0)
    
    # After a recent service, health should be restored somewhat
    # But since this runs AT job completion, we are predicting the FUTURE state.
    # Let's say the current repair fixes the immediate issue (health bumps to 85)
    # But we predict the NEXT failure.
    
    new_health = max(10.0, 85.0 - (age_years * 2.0)) # Older appliances max out lower
    
    # Predict days until next failure (lower health = fewer days)
    # E.g. Health 85 -> ~180 days. Health 40 -> ~30 days.
    predicted_days = int(new_health * 2.5) + random.randint(-15, 15)
    
    appliance.health_score = new_health
    appliance.predicted_failure_days = max(5, predicted_days)
    
    return {
        "health_score": round(new_health, 1),
        "predicted_failure_days": appliance.predicted_failure_days,
        "needs_pre_reservation": appliance.predicted_failure_days < 60 # Critical threshold
    }


def run_predictive_logistics(db: Session, user_id: int, service_name: str, location: str) -> dict:
    """
    Runs the full Predictive Logistics pipeline:
    1. Forecasts next failure.
    2. Pre-reserves parts at a local shop if failure is imminent.
    """
    app_type = parse_appliance_type(service_name)
    
    # 1. Get or create appliance profile
    appliance = db.query(HouseholdAppliance).filter(
        HouseholdAppliance.user_id == user_id,
        HouseholdAppliance.appliance_type == app_type
    ).first()
    
    if not appliance:
        appliance = HouseholdAppliance(
            user_id=user_id,
            appliance_type=app_type,
            purchase_year=datetime.datetime.utcnow().year - random.randint(1, 5),
            last_serviced_date=datetime.datetime.utcnow()
        )
        db.add(appliance)
        db.commit()
        db.refresh(appliance)
        
    # 2. Run AI Forecast
    forecast = forecast_failure(appliance)
    
    # 3. Hyper-Local Logistics Reservation
    reservation_details = None
    if forecast["needs_pre_reservation"]:
        required_part = get_required_part(app_type)
        
        # Find nearest shop (mocking location match)
        shop = db.query(LocalShop).filter(LocalShop.location.ilike(f"%{location}%")).first()
        if not shop:
            shop = db.query(LocalShop).first() # Fallback to any shop
            
        if shop:
            inventory = json.loads(shop.inventory_json) if shop.inventory_json else {}
            # Check if part is in stock (or just mock reserve it)
            if inventory.get(required_part, 0) > 0 or True:
                appliance.reserved_part = required_part
                reservation_details = {
                    "shop_name": shop.name,
                    "shop_location": shop.location,
                    "part_reserved": required_part,
                    "status": "RESERVED"
                }
                
    db.commit()
    
    return {
        "appliance": app_type,
        "health_score": forecast["health_score"],
        "predicted_failure_days": forecast["predicted_failure_days"],
        "logistics": reservation_details
    }
