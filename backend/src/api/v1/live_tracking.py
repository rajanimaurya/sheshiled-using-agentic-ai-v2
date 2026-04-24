# ─────────────────────────────────────────────────────────────────────────────
# SheShield - LIVE LOCATION API ENDPOINTS
#
# New Endpoints:
#   POST   /api/v1/live/start       → Start live tracking
#   POST   /api/v1/live/update      → Update location (every 5-10 sec)
#   GET    /api/v1/live/status      → Get current tracking status
#   GET    /api/v1/live/map-data    → Get live map data
#   GET    /api/v1/live/family      → Get family dashboard data
#   POST   /api/v1/live/end         → End tracking session
#
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api.dependencies.auth import get_current_user
from src.services.live_location_service import LiveLocationTracker
from src.services.sos_nearby_integration import SheShieldSOSNearby
from typing import Optional

router = APIRouter(tags=["live_tracking"])


# ========== PYDANTIC MODELS ==========

class LocationUpdate(BaseModel):
    """Live location update from frontend"""
    latitude: float
    longitude: float
    radius: int = 2000


class LiveTrackingStart(BaseModel):
    """Start live tracking session"""
    latitude: float
    longitude: float
    radius: int = 2000


# ========== ENDPOINTS ==========

@router.post("/live/start")
async def start_live_tracking(
    data: LiveTrackingStart,
    current_user = Depends(get_current_user)
):
    """
    🚨 START LIVE TRACKING SESSION
    
    Called when user clicks SOS.
    Creates session and begins continuous tracking.
    
    Request:
    {
        "latitude": 26.9124,
        "longitude": 75.7873,
        "radius": 2000
    }
    
    Response:
    {
        "status": "LIVE_TRACKING_STARTED",
        "session_id": "user_123",
        "started_at": "2026-04-20T...",
        "nearest_safe_place": {...}
    }
    """
    
    # Create tracking session
    session = LiveLocationTracker.create_session(current_user.id)
    
    # Find initial nearby places
    nearby_places = SheShieldSOSNearby.find_nearby_places(
        data.latitude,
        data.longitude,
        data.radius
    )
    
    # Convert to dict format
    nearby_dict = {
        k: v.to_dict() if v else None
        for k, v in nearby_places.items()
    }
    
    # Update initial location
    updated = LiveLocationTracker.update_location(
        current_user.id,
        data.latitude,
        data.longitude,
        nearby_dict
    )
    
    return {
        "status": "LIVE_TRACKING_STARTED",
        "user_id": current_user.id,
        "session_started_at": session["started_at"],
        "current_location": {
            "latitude": data.latitude,
            "longitude": data.longitude
        },
        "nearest_safe_place": updated["nearest_safe_place"],
        "message": "Live tracking active! Location updating every 5-10 seconds."
    }


@router.post("/live/update")
async def update_live_location(
    data: LocationUpdate,
    current_user = Depends(get_current_user)
):
    """
    📍 UPDATE LIVE LOCATION
    
    Called every 5-10 seconds from frontend.
    Updates location + recalculates nearby places + route.
    
    This keeps live tracking data fresh!
    
    Request:
    {
        "latitude": 26.91245,
        "longitude": 75.78735
    }
    
    Response:
    {
        "status": "LOCATION_UPDATED",
        "current_location": {...},
        "nearest_safe_place": {...},
        "total_distance_traveled": 450
    }
    """
    
    # Check if session exists
    from src.services.live_location_service import LIVE_TRACKING_SESSIONS
    if current_user.id not in LIVE_TRACKING_SESSIONS:
        raise HTTPException(
            status_code=400,
            detail="No active tracking session. Start tracking first."
        )
    
    # Find nearby places from current location
    nearby_places = SheShieldSOSNearby.find_nearby_places(
        data.latitude,
        data.longitude,
        data.radius
    )
    
    nearby_dict = {
        k: v.to_dict() if v else None
        for k, v in nearby_places.items()
    }
    
    # Update location and get new data
    updated = LiveLocationTracker.update_location(
        current_user.id,
        data.latitude,
        data.longitude,
        nearby_dict
    )
    
    return {
        "status": "LOCATION_UPDATED",
        "timestamp": updated["location_history"][-1]["timestamp"],
        "current_location": {
            "latitude": data.latitude,
            "longitude": data.longitude
        },
        "nearest_safe_place": updated["nearest_safe_place"],
        "all_nearby_places": updated["nearby_places"],
        "total_distance_traveled_m": updated["total_distance_traveled"],
        "locations_tracked": len(updated["location_history"])
    }


@router.get("/live/status")
async def get_tracking_status(
    current_user = Depends(get_current_user)
):
    """
    Get current live tracking status.
    
    Response shows:
    - Current location
    - Nearest safe place
    - Route to safety
    - Distance traveled
    - All nearby places
    """
    
    data = LiveLocationTracker.get_session_data(current_user.id)
    
    if not data:
        raise HTTPException(
            status_code=404,
            detail="No active tracking session"
        )
    
    return {
        "status": "LIVE_TRACKING_ACTIVE",
        "user_id": current_user.id,
        "started_at": data["started_at"],
        "current_location": data["current_location"],
        "nearest_safe_place": data["nearest_safe_place"],
        "route_to_safety": data["route_to_safety"],
        "nearby_places": data["nearby_places"],
        "tracking_stats": {
            "locations_tracked": data["location_count"],
            "total_distance_m": data["total_distance_traveled"]
        }
    }


@router.get("/live/map-data")
async def get_live_map_data(
    current_user = Depends(get_current_user)
):
    """
    📊 GET LIVE MAP DATA
    
    For frontend live map display.
    Shows:
    - Current location marker
    - All nearby places
    - Route to nearest safe place
    - Movement summary
    
    Use this to display live map!
    """
    
    return LiveLocationTracker.get_live_map_data(current_user.id)


@router.get("/live/family")
async def get_family_dashboard(
    current_user = Depends(get_current_user)
):
    """
    👨‍👩‍👧 FAMILY DASHBOARD DATA
    
    Data for emergency contacts.
    Shows:
    - Live location
    - ALL nearby places with live distances
    - Nearest safe place
    - Route to safety
    - Full movement history
    - Map embed links
    
    Share this link with family! They see EVERYTHING live!
    """
    
    return LiveLocationTracker.get_family_dashboard(current_user.id)


@router.post("/live/end")
async def end_live_tracking(
    current_user = Depends(get_current_user)
):
    """
    Stop live tracking session.
    
    Response includes final summary:
    - Total distance traveled
    - Locations tracked
    - Duration
    - Final location
    """
    
    session = LiveLocationTracker.end_session(current_user.id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No active tracking session"
        )
    
    # Calculate duration
    from datetime import datetime
    started = datetime.fromisoformat(session["started_at"])
    ended = datetime.fromisoformat(session["ended_at"])
    duration = (ended - started).total_seconds() / 60
    
    return {
        "status": "TRACKING_ENDED",
        "summary": {
            "started_at": session["started_at"],
            "ended_at": session["ended_at"],
            "duration_minutes": round(duration, 2),
            "total_distance_m": session["total_distance_traveled"],
            "locations_tracked": len(session["location_history"]),
            "final_location": session["location_history"][-1] if session["location_history"] else None
        }
    }
