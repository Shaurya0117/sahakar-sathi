from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime

from app.database.session import Base

class HouseholdAppliance(Base):
    __tablename__ = "household_appliances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appliance_type = Column(String(100), nullable=False)
    brand = Column(String(100))
    purchase_year = Column(Integer)
    last_serviced_date = Column(DateTime)
    health_score = Column(Float, default=100.0)
    predicted_failure_days = Column(Integer)
    reserved_part = Column(String(255))

    # Relationship to user
    owner = relationship("User", backref="appliances")
