from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.database.session import Base

class AIActivityLog(Base):
    __tablename__ = "ai_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    location = Column(String(255), nullable=False)
    travel_time = Column(String(50))
    risk_level = Column(String(20)) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())