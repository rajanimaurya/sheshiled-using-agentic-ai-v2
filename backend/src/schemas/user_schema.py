from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., pattern=r"^[6-9]\d{9}$")
    password: str = Field(..., min_length=6)
    
    # Flattened fields
    emergency_name: Optional[str] = None
    emergency_email: Optional[str] = None
    emergency_phone: Optional[str] = None
    emergency_relation: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def username_lowercase(cls, value):
        return value.lower()


class EmergencyContactBase(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r"^[6-9]\d{9}$")
    relation: Optional[str] = Field(None, min_length=2, max_length=50)

class EmergencyContactOut(EmergencyContactBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)


class UserOut(BaseModel):
    id: int
    username: str
    name: str
    email: EmailStr
    phone: str
    is_active: bool
    role: str
    emergency_contact: Optional[EmergencyContactOut] = None 
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^[6-9]\d{9}$")
    is_active: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    login_id: str = Field(..., description="Enter Username, Email, or Phone Number")
    password: str


class SecretCodeRequest(BaseModel):
    """POST /api/v1/users/me/secret-code ka body."""
    secret_code: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Koi bhi word jo suspicious na lage — e.g. 'neebu', 'chai', 'movie'"
    )


class SecretCodeOut(BaseModel):
    """GET /api/v1/users/me/secret-code ka response."""
    secret_code: Optional[str] = None
    message: str
