# ─────────────────────────────────────────────────────────────────────────────
# SheShield — AI Router
#
# Endpoints:
#   POST /api/v1/ai/report   → safety report (5 workers + judge)
#   POST /api/v1/ai/alert    → SOS trigger → SMS + Call + Email
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

router = APIRouter(tags=["AI Safety"])


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
# 2. SOS ALERT
# ─────────────────────────────────────────────
@router.post("/alert")
async def send_sos_alert(
    data: AlertRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """
    🚨 Trigger SOS:
    - Sends SMS + Call
    - Sends Email with nearby places
    - Runs in background
    """
    contacts_list = [c.dict() for c in data.contacts]
    
    # Get nearby places if GPS coordinates were provided
    nearby_places = None
    if data.latitude is not None and data.longitude is not None:
        from src.services.nearby_places_fix import NearbyPlacesFinder
        try:
            places = NearbyPlacesFinder.find_all_places(
                data.latitude, data.longitude, 2000
            )
            nearby_places = {k: v.to_dict() if v else None for k, v in places.items()}
        except Exception as e:
            print(f"⚠️ Could not fetch nearby places: {e}")
            nearby_places = None

    background_tasks.add_task(
        dispatch_alerts,
        contacts=contacts_list,
        user_name=current_user.name,
        location=data.location,
        nearby_places=nearby_places
    )

    return {
        "status": "dispatched",
        "message": f"Alert is being sent to {len(contacts_list)} contact(s).",
    }


# ─────────────────────────────────────────────
# 3. NEARBY PLACES
# ─────────────────────────────────────────────
class NearbyRequest(BaseModel):
    latitude: float
    longitude: float
    radius: int = 3000  # meters


@router.post("/nearby")
async def get_nearby_places(data: NearbyRequest):
    """
    Find nearby safety places using Overpass API.
    Returns text summary + structured list.
    """

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    CATEGORIES = {
        "hospital": {
            "queries": [
                '["amenity"="hospital"]',
                '["amenity"="clinic"]',
                '["healthcare"="hospital"]',
                '["healthcare"="clinic"]',
            ],
            "label": "Hospital",
        },
        "police": {
            "queries": ['["amenity"="police"]'],
            "label": "Police Station",
        },
        "mall": {
            "queries": [
                '["shop"="supermarket"]',
                '["shop"="department_store"]',
                '["shop"="shopping_centre"]',
                '["amenity"="marketplace"]',
                '["amenity"="shopping_centre"]',
            ],
            "label": "Mall/Market",
        },
        "restaurant": {
            "queries": [
                '["amenity"="restaurant"]',
                '["amenity"="cafe"]',
                '["amenity"="fast_food"]',
                '["amenity"="food_court"]',
            ],
            "label": "Restaurant",
        },
    }

    def haversine(lat1, lon1, lat2, lon2):
        R = 6_371_000
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)

        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    places = []
    text_lines = []

    async with httpx.AsyncClient() as client:
        for key, meta in CATEGORIES.items():

            query_parts = []
            for tag in meta["queries"]:
                query_parts.append(
                    f'node{tag}(around:{data.radius},{data.latitude},{data.longitude});'
                )
                query_parts.append(
                    f'way{tag}(around:{data.radius},{data.latitude},{data.longitude});'
                )

            queries = "\n".join(query_parts)

            query = f"""
            [out:json][timeout:25];
            (
              {queries}
            );
            out center 100;
            """

            try:
                res = await client.post(
                    OVERPASS_URL, data={"data": query}, timeout=30
                )

                elements = res.json().get("elements", [])

                valid_places = []

                for el in elements:
                    el_lat = el.get("lat") or el.get("center", {}).get("lat")
                    el_lon = el.get("lon") or el.get("center", {}).get("lon")

                    if not el_lat or not el_lon:
                        continue

                    dist = haversine(
                        data.latitude, data.longitude, el_lat, el_lon
                    )

                    if dist <= data.radius:
                        valid_places.append(
                            {
                                "dist": dist,
                                "el": el,
                                "lat": el_lat,
                                "lon": el_lon,
                            }
                        )

                valid_places.sort(key=lambda x: x["dist"])

                for idx, place_data in enumerate(valid_places[:3]):
                    el = place_data["el"]

                    place_obj = {
                        "type": key,
                        "name": el.get("tags", {}).get("name", meta["label"]),
                        "lat": place_data["lat"],
                        "lng": place_data["lon"],
                        "distance": place_data["dist"],
                        "address": (
                            el.get("tags", {}).get("addr:street")
                            or el.get("tags", {}).get("addr:full")
                            or el.get("tags", {}).get("addr:city")
                            or ""
                        ),
                    }

                    places.append(place_obj)

                    if idx == 0:
                        icons = {
                            "hospital": "🏥",
                            "police": "🚔",
                            "restaurant": "🍽️",
                            "mall": "🏬",
                        }
                        text_lines.append(
                            f"{icons.get(key,'📍')} {place_obj['name']} — {place_obj['distance']}m"
                        )

            except Exception as e:
                print(f"Error fetching {key}: {e}")

            await asyncio.sleep(0.5)

    return {
        "nearby_places": "\n".join(text_lines)
        if text_lines
        else "No nearby places found. Try increasing the radius.",
        "places": places,
    }


# ─────────────────────────────────────────────
# 3.5 FILTER PLACES (Map Filters)
# ─────────────────────────────────────────────

class NearbyFilterRequest(BaseModel):
    """Filter request for specific place type"""
    latitude: float
    longitude: float
    filter_type: str  # hospital, police, mall, restaurant
    radius: int = 2000


@router.post("/nearby-filter")
async def filter_nearby_places(
    data: NearbyFilterRequest,
    current_user=Depends(get_current_user)
):
    """
    🔍 FILTER NEARBY PLACES
    
    Get specific place type (Hospital, Police, Mall, Restaurant)
    Used by filter buttons on Safe Route Map
    
    Request:
    {
      "latitude": 26.9124,
      "longitude": 75.7873,
      "filter_type": "hospital",
      "radius": 2000
    }
    
    Response:
    {
      "status": "FOUND",
      "place": {
        "name": "Apollo Hospital",
        "type": "Hospital",
        "distance_m": 680,
        "lat": 26.918,
        "lng": 75.785
      }
    }
    """
    
    from src.services.nearby_places_fix import NearbyPlacesFinder
    
    print(f"🔍 Filter: {data.filter_type} at {data.latitude}, {data.longitude}")
    
    try:
        place = NearbyPlacesFinder.find_by_filter(
            data.latitude,
            data.longitude,
            data.filter_type,
            data.radius
        )
        
        if not place:
            return {
                "status": "NOT_FOUND",
                "filter_type": data.filter_type,
                "message": f"No {data.filter_type} found nearby",
                "place": None
            }
        
        return {
            "status": "FOUND",
            "filter_type": data.filter_type,
            "place": place.to_dict(),
            "maps_link": f"https://maps.google.com?q={place.lat},{place.lng}"
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e),
            "place": None
        }


# ─────────────────────────────────────────────
# 4. CHAT (Secret Code SOS)
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
# 5. GEOCODE
# ─────────────────────────────────────────────
class GeocodeRequest(BaseModel):
    query: str


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