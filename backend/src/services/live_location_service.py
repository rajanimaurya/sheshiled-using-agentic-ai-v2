# ─────────────────────────────────────────────────────────────────────────────
# SheShield - LIVE LOCATION TRACKING SERVICE
#
# Features:
#   ✓ Continuous GPS tracking (every 5-10 seconds)
#   ✓ Real-time nearby places updates
#   ✓ Live route calculation
#   ✓ Location history storage
#   ✓ Family dashboard data
#
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json

# For storing live sessions
LIVE_TRACKING_SESSIONS = {}  # {user_id: {location_history, nearby_places, route}}


@dataclass
class LocationPoint:
    """Single GPS location point"""
    latitude: float
    longitude: float
    timestamp: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class NearbyPlaceUpdate:
    """Nearby place with real-time distance"""
    name: str
    place_type: str
    latitude: float
    longitude: float
    address: str
    distance_m: int  # Current distance in meters
    icon: str
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.place_type,
            "lat": self.latitude,
            "lng": self.longitude,
            "address": self.address,
            "distance_m": self.distance_m,
            "icon": self.icon
        }


class LiveLocationTracker:
    """
    Real-time location tracking system.
    Tracks user movement continuously and updates nearby places live.
    """

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        """Calculate distance in metres"""
        R = 6_371_000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    @staticmethod
    def create_session(user_id: int) -> Dict:
        """
        Create a new live tracking session for user.
        Called when SOS is triggered.
        """
        session = {
            "user_id": user_id,
            "started_at": datetime.now().isoformat(),
            "location_history": [],  # [{lat, lon, timestamp}]
            "nearby_places": {},     # {type: {name, dist, ...}}
            "current_location": None,
            "nearest_safe_place": None,
            "route_to_safety": None,
            "total_distance_traveled": 0
        }
        LIVE_TRACKING_SESSIONS[user_id] = session
        return session

    @staticmethod
    def end_session(user_id: int) -> Optional[Dict]:
        """End tracking session"""
        if user_id in LIVE_TRACKING_SESSIONS:
            session = LIVE_TRACKING_SESSIONS[user_id]
            session["ended_at"] = datetime.now().isoformat()
            return session
        return None

    @staticmethod
    def update_location(
        user_id: int,
        latitude: float,
        longitude: float,
        nearby_places: Dict = None
    ) -> Dict:
        """
        Update location for live tracking.
        Called every 5-10 seconds from frontend.
        
        Returns: Updated tracking data with live nearby places
        """
        
        if user_id not in LIVE_TRACKING_SESSIONS:
            return {"error": "No active session"}

        session = LIVE_TRACKING_SESSIONS[user_id]
        current_time = datetime.now().isoformat()

        # Create location point
        location_point = {
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": current_time
        }

        # Add to history
        session["location_history"].append(location_point)
        session["current_location"] = location_point

        # Calculate distance traveled
        if len(session["location_history"]) > 1:
            prev = session["location_history"][-2]
            dist = LiveLocationTracker.haversine_distance(
                prev["latitude"], prev["longitude"],
                latitude, longitude
            )
            session["total_distance_traveled"] += dist

        # Update nearby places with live distances
        if nearby_places:
            for category, place in nearby_places.items():
                if place:
                    # Recalculate distance from current location
                    live_distance = LiveLocationTracker.haversine_distance(
                        latitude, longitude,
                        place["lat"], place["lng"]
                    )
                    
                    session["nearby_places"][category] = {
                        "name": place["name"],
                        "type": place["type"],
                        "lat": place["lat"],
                        "lng": place["lng"],
                        "address": place["address"],
                        "distance_m": live_distance,  # ← LIVE DISTANCE!
                        "icon": place.get("icon", "📍"),
                        "last_updated": current_time
                    }

            # Find nearest safe place
            safe_distances = [
                (k, v["distance_m"]) 
                for k, v in session["nearby_places"].items()
                if v["distance_m"] < 5000  # Within 5km
            ]
            
            if safe_distances:
                nearest_type, nearest_dist = min(safe_distances, key=lambda x: x[1])
                nearest_place = session["nearby_places"][nearest_type]
                
                session["nearest_safe_place"] = {
                    "type": nearest_type,
                    "name": nearest_place["name"],
                    "distance_m": nearest_dist,
                    "lat": nearest_place["lat"],
                    "lng": nearest_place["lng"],
                    "maps_link": f"https://www.google.com/maps/dir/?api=1&origin={latitude},{longitude}&destination={nearest_place['lat']},{nearest_place['lng']}&travelmode=driving"
                }
                
                session["route_to_safety"] = {
                    "from": {"lat": latitude, "lng": longitude},
                    "to": {
                        "lat": nearest_place["lat"],
                        "lng": nearest_place["lng"],
                        "name": nearest_place["name"]
                    },
                    "distance_m": nearest_dist,
                    "maps_embed": f"https://maps.google.com/maps?q={latitude},{longitude}"
                }

        return session

    @staticmethod
    def get_session_data(user_id: int) -> Optional[Dict]:
        """Get current session data"""
        if user_id not in LIVE_TRACKING_SESSIONS:
            return None
        
        session = LIVE_TRACKING_SESSIONS[user_id]
        return {
            "user_id": session["user_id"],
            "started_at": session["started_at"],
            "current_location": session["current_location"],
            "location_history": session["location_history"],
            "nearby_places": session["nearby_places"],
            "nearest_safe_place": session["nearest_safe_place"],
            "route_to_safety": session["route_to_safety"],
            "total_distance_traveled": session["total_distance_traveled"],
            "location_count": len(session["location_history"])
        }

    @staticmethod
    def get_live_map_data(user_id: int) -> Dict:
        """
        Get data for live map display.
        Shows current location + nearby places + route.
        """
        session_data = LiveLocationTracker.get_session_data(user_id)
        
        if not session_data:
            return {"error": "No active session"}

        return {
            "status": "LIVE_TRACKING",
            "current_location": session_data["current_location"],
            "nearby_places": session_data["nearby_places"],
            "nearest_safe_place": session_data["nearest_safe_place"],
            "route": session_data["route_to_safety"],
            "movement_summary": {
                "locations_tracked": session_data["location_count"],
                "total_distance_m": session_data["total_distance_traveled"],
                "duration_minutes": (
                    (datetime.fromisoformat(
                        datetime.now().isoformat()
                    ) - datetime.fromisoformat(
                        session_data["started_at"]
                    )).total_seconds() / 60
                )
            }
        }

    @staticmethod
    def get_family_dashboard(user_id: int) -> Dict:
        """
        Get data for family/emergency contacts dashboard.
        Shows live location + nearby places + all info.
        """
        session_data = LiveLocationTracker.get_session_data(user_id)
        
        if not session_data:
            return {"error": "No active session"}

        current = session_data["current_location"]
        
        return {
            "status": "LIVE_TRACKING_ACTIVE",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            
            # Live Location
            "location": {
                "latitude": current["latitude"],
                "longitude": current["longitude"],
                "map_link": f"https://maps.google.com?q={current['latitude']},{current['longitude']}",
                "map_embed": f"https://maps.google.com/maps?q={current['latitude']},{current['longitude']}"
            },
            
            # All Nearby Places (Live Distances!)
            "nearby_places": {
                "police": session_data["nearby_places"].get("police"),
                "hospital": session_data["nearby_places"].get("hospital"),
                "mall": session_data["nearby_places"].get("mall"),
                "restaurant": session_data["nearby_places"].get("restaurant")
            },
            
            # Nearest Safe Place
            "nearest_safe_place": session_data["nearest_safe_place"],
            
            # Route to nearest place
            "route_to_safety": session_data["route_to_safety"],
            
            # Movement tracking
            "movement": {
                "locations_tracked": session_data["location_count"],
                "distance_traveled_m": session_data["total_distance_traveled"],
                "started_at": session_data["started_at"],
                "current_time": datetime.now().isoformat()
            },
            
            # Last known positions
            "location_history": session_data["location_history"][-10:]  # Last 10 points
        }
