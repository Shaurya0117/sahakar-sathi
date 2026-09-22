from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime

from app.database.session import Base

class LocalShop(Base):
    __tablename__ = "local_shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    inventory_json = Column(Text, default="{}")
