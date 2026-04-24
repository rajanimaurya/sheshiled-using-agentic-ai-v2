from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database.session import Base

class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=True)
    phone = Column(String(15), nullable=True)
    email = Column(String, nullable=True)
    relation = Column(String(50), nullable=True)
    
    
    user = relationship("User", back_populates="emergency_contacts")