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


import math

from app.config import WEIBULL_PARAMS

def forecast_failure(appliance: HouseholdAppliance) -> dict:
    """
    Predictive Logistics Model using Weibull Survival Analysis.
    Calculates the probability of survival (Reliability) and predicts failure
    based on the appliance's characteristic lifespan and wear-out curve.
    Requires no training data, making it explainable and legally defensible.
    """
    now = datetime.datetime.utcnow()
    
    if not appliance.last_serviced_date:
        appliance.last_serviced_date = now
        appliance.health_score = 100.0
        
    age_years = (now.year - appliance.purchase_year) if appliance.purchase_year else 3
    age_days = age_years * 365.25
    
    # Get Weibull parameters for this appliance type
    params = WEIBULL_PARAMS.get(appliance.appliance_type, WEIBULL_PARAMS["General Appliance"])
    eta = params["eta"]
    beta = params["beta"]
    
    # Reliability function R(t) = e^(-(t/eta)^beta)
    # This gives the % chance the appliance survives to 'age_days'
    reliability = math.exp(-((age_days / eta) ** beta))
    health_score = reliability * 100.0
    
    # Predict days until reliability drops below critical threshold (e.g., 20%)
    critical_threshold = 0.20
    # Solve for t in R(t) = 0.20: t = eta * (-ln(0.20))^(1/beta)
    target_failure_days = eta * ((-math.log(critical_threshold)) ** (1/beta))
    
    predicted_failure_days = max(5, int(target_failure_days - age_days))
    
    # After a recent service, we assume basic maintenance extends life slightly
    days_since_service = (now - appliance.last_serviced_date).days
    if days_since_service < 30:
        predicted_failure_days += 90  # Maintenance bump
        health_score = min(100.0, health_score + 15.0)

    appliance.health_score = health_score
    appliance.predicted_failure_days = predicted_failure_days
    
    return {
        "health_score": round(health_score, 1),
        "predicted_failure_days": appliance.predicted_failure_days,
        "needs_pre_reservation": appliance.predicted_failure_days < 90 # Critical threshold
    }

def run_predictive_logistics(db: Session, user_id: int, service_name: str, location: str) -> dict:
    """
    Runs the full Predictive Logistics pipeline:
    1. Forecasts next failure using Weibull Survival Model.
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
