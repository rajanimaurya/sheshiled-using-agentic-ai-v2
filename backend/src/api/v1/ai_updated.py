# ─────────────────────────────────────────────────────────────────────────────
# SheShield — AI Router (Updated)
#
# Endpoints:
#   POST /api/v1/ai/report   → safety report (5 workers + judge)
#   POST /api/v1/ai/alert    → SOS trigger with nearby places
#   POST /api/v1/ai/sos-trigger → New integrated SOS endpoint
#   POST /api/v1/ai/chat     → conversational safety check + secret code SOS
#   POST /api/v1/ai/nearby   → nearest places via GPS coordinates
#   POST /api/v1/ai/geocode  → location name → coordinates
# ─────────────────────────────────────────────────────────────────────────────

import math
import asyncio
import httpx

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from src.database.session import get_db
from src.api.dependencies.auth import get_current_user
from src.services.ai_service import AISafetyService
from src.schemas.ai_schema import (
    AIReportRequest,
    AlertRequest,
    ChatRequest,
    ChatResponse,
)

from src.services.chat_service import chat_with_ai
from src.services.alert_service import dispatch_alerts
from src.services.user_service import UserService
from src.models.emergency import EmergencyContact
from src.services.sos_nearby_integration import trigger_sos_emergency

router = APIRouter(tags=["AI Safety"])


# ─────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────
class SOSTriggerRequest(BaseModel):
    """Request to trigger SOS with location and email"""
    latitude: float
    longitude: float
    recipient_emails: list[str] = []  # Empty = use emergency contacts
    timestamp: str = None


class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    radius: int = 2000  # meters


class GeocodeRequest(BaseModel):
    query: str


# ─────────────────────────────────────────────
# 1. SAFETY REPORT
# ─────────────────────────────────────────────
@router.post("/report")
async def get_safety_report(
    data: AIReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate safety report using multiple LLM workers and a judge model.
    """
    report = await AISafetyService.get_safety_report(
        data.location, data.time, data.intent
    )

    await AISafetyService.log_activity(
        db, current_user.id, data.location, data.time, report
    )

    return {"report": report}


# ─────────────────────────────────────────────
# 2. SOS TRIGGER (NEW - Integrated)
# ─────────────────────────────────────────────
@router.post("/sos-trigger")
async def trigger_sos(
    data: SOSTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    NEW: Integrated SOS trigger with nearby places.
    
    - Sends email to recipient(s) with:
      - Current location (GPS)
      - Nearby hospitals, police, restaurants, malls
      - Google Maps link with directions
    
    - Returns:
      - Map links for frontend
      - Nearby places info
      - Email status
    """
    from datetime import datetime
    
    # Get email recipients
    recipient_emails = data.recipient_emails
    if not recipient_emails:
        # Fallback to emergency contacts from DB
        result = await db.execute(
            select(EmergencyContact).where(EmergencyContact.user_id == current_user.id)
        )
        contacts = result.scalars().all()
        recipient_emails = [c.email for c in contacts if hasattr(c, "email") and c.email]
    
    if not recipient_emails:
        return {
            "success": False,
            "message": "No email recipients found. Please add emergency contacts.",
        }
    
    # Prepare timestamp
    timestamp = data.timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    
    # Call the integrated SOS + Nearby function
    sos_result = await trigger_sos_emergency(
        recipient_emails=recipient_emails,
        user_name=current_user.name or "a SheShield user",
        latitude=data.latitude,
        longitude=data.longitude,
        timestamp=timestamp
    )
    
    # Log activity
    location_str = f"{data.latitude},{data.longitude}"
    await AISafetyService.log_activity(
        db, 
        current_user.id, 
        location_str, 
        timestamp, 
        f"SOS Triggered. Nearby places fetched."
    )
    
    return sos_result


# ─────────────────────────────────────────────
# 3. LEGACY SOS ALERT (backward compatible)
# ─────────────────────────────────────────────
@router.post("/alert")
async def send_sos_alert(
    data: AlertRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """
    Legacy SOS Alert endpoint.
    Triggers SMS + Call + Email (existing functionality)
    """
    contacts_list = [c.dict() for c in data.contacts]

    background_tasks.add_task(
        dispatch_alerts,
        contacts=contacts_list,
        user_name=current_user.name,
        location=data.location,
    )

    return {
        "status": "dispatched",
        "message": f"Alert is being sent to {len(contacts_list)} contact(s).",
    }


# ─────────────────────────────────────────────
# 4. NEARBY PLACES (Enhanced with Google API)
# ─────────────────────────────────────────────
@router.post("/nearby")
async def get_nearby_places(data: NearbyRequest):
    """
    Find nearby safety places using Google Places API.
    Returns text summary + structured list + map markers.
    """
    from src.services.sos_nearby_integration import SheShieldSOSNearby

    nearby_places = SheShieldSOSNearby.find_nearby_places(
        data.latitude, data.longitude, data.radius
    )

    # Format response
    text_lines = []
    places_list = []

    icons = {
        "hospital": "🏥",
        "police": "🚔",
        "mall": "🏬",
        "restaurant": "🍽️",
    }

    for key, place in nearby_places.items():
        if place:
            icon = icons.get(key, "📍")
            text_lines.append(f"{icon} {place.name} — {place.distance}m ({place.address})")
            places_list.append(place.to_dict())

    # Map links
    map_links = SheShieldSOSNearby.get_maps_embed_link(data.latitude, data.longitude, nearby_places)

    return {
        "nearby_places": "\n".join(text_lines) if text_lines else "No nearby places found.",
        "places": places_list,
        "map_links": map_links,
        "user_location": {
            "latitude": data.latitude,
            "longitude": data.longitude,
        }
    }


# ─────────────────────────────────────────────
# 5. CHAT (Secret Code SOS)
# ─────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
async def chat_safety(
    data: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Conversational safety system with secret SOS trigger.
    """

    message = data.message.strip()

    # Exit cases
    if message.lower() in ("bye", "exit", "quit", "goodbye"):
        return ChatResponse(
            ready=False,
            reply="Take care! Stay safe 💕",
        )

    # Secret code detection
    is_secret_code = await UserService.verify_secret_code(current_user, message)

    if is_secret_code:
        result = await db.execute(
            select(EmergencyContact).where(
                EmergencyContact.user_id == current_user.id
            )
        )

        contacts = result.scalars().all()

        contacts_list = [
            {"name": c.name, "phone": c.phone, "email": getattr(c, "email", None)}
            for c in contacts
        ]

        if contacts_list:
            background_tasks.add_task(
                dispatch_alerts,
                contacts=contacts_list,
                user_name=current_user.name,
                location="Triggered via secret code",
            )

        return ChatResponse(
            ready=False,
            reply="Yes, tell me where you want to go 😊",
            sos_triggered=True,
        )

    # Normal chat flow
    full_history = [{"role": m.role, "content": m.content} for m in data.history]
    full_history.append({"role": "user", "content": message})

    parsed = await chat_with_ai(full_history)

    if not parsed.get("ready"):
        return ChatResponse(
            ready=False,
            reply=parsed.get("reply", "Tell me, where do you want to go? 😊"),
        )

    location = parsed["location"]
    time = parsed["time"]
    intent = parsed.get("intent", "general")

    report = await AISafetyService.get_safety_report(location, time, intent)

    await AISafetyService.log_activity(
        db, current_user.id, location, time, report
    )

    return ChatResponse(
        ready=True,
        reply=parsed.get("reply", f"Safety check done for {location} ✅"),
        location=location,
        time=time,
        report=report,
    )


# ─────────────────────────────────────────────
# 6. GEOCODE
# ─────────────────────────────────────────────
@router.post("/geocode")
async def geocode_location(data: GeocodeRequest):
    """
    Convert location name → latitude & longitude using Nominatim.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": data.query,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "in",
                    "accept-language": "en",
                },
                headers={"User-Agent": "SheShield-App/1.0"},
                timeout=10,
            )

            results = response.json()

            if results:
                return {
                    "found": True,
                    "lat": float(results[0]["lat"]),
                    "lng": float(results[0]["lon"]),
                    "display_name": results[0]["display_name"],
                }

            return {"found": False}

    except Exception as e:
        return {"found": False, "error": str(e)}
