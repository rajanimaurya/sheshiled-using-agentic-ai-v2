
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List



class AIReportRequest(BaseModel):
    location: str
    time: str
    intent: str = "general"   # travel | stay | return | general


class AIHistoryOut(BaseModel):
    id: int
    location: str
    travel_time: str
    risk_level: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContactInfo(BaseModel):
    """Ek emergency contact ka data — frontend se aata hai SOS trigger par."""
    name:  str
    phone: Optional[str] = None   # +91XXXXXXXXXX format
    email: Optional[str] = None


class AlertRequest(BaseModel):
    """POST /api/v1/ai/alert ka body."""
    contacts: List[ContactInfo]
    location: Optional[str] = "Location unavailable"
    latitude: Optional[float] = None    # GPS latitude (frontend se aata hai)
    longitude: Optional[float] = None   # GPS longitude (frontend se aata hai)




class ChatMessage(BaseModel):
    """Ek message — user ya assistant ka."""
    role:    str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """
    POST /api/v1/ai/chat ka body.

    Frontend poora conversation history bhejega har turn mein.
    Backend stateless hai — history frontend pe store hoti hai.
    """
    history: List[ChatMessage] = []   #(user + assistant dono)
    message: str                      # current user message


class ChatResponse(BaseModel):
    """
    /chat endpoint ka response.

    ready=False → sirf reply return hoga, report nahi.
    ready=True  → report bhi aayega (safety analysis complete).
    """
    ready:         bool
    reply:         str
    location:      Optional[str]  = None
    time:          Optional[str]  = None
    report:        Optional[dict] = None   # AISafetyService.get_safety_report() ka output
    sos_triggered: bool           = False  # True → secret code detect hua, SOS fire hua