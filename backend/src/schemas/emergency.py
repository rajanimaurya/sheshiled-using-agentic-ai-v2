from pydantic import BaseModel, Field
from typing import Optional


class EmergencyContactCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^[6-9]\d{9}$")
    email: Optional[str] = None
    relation: Optional[str] = Field(None, min_length=2, max_length=50)


class EmergencyContactResponse(EmergencyContactCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True