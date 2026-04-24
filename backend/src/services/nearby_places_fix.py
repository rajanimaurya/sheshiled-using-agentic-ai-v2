# ─────────────────────────────────────────────────────────────────────────────
# SHESHIELD — NEARBY PLACES FINDER
#
# Uses Google Places API to find nearest:
#   Hospital, Police Station, Mall, Restaurant
#
# Called by:
#   - alert endpoint (SOS email mein places include karne ke liye)
#   - nearby-filter endpoint (map filter buttons ke liye)
# ─────────────────────────────────────────────────────────────────────────────

import os
import math
import requests
from typing import Dict, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class NearbyPlace:
    name:       str
    place_type: str
    distance:   int     # metres
    address:    str
    lat:        float
    lng:        float

    def to_dict(self) -> dict:
        return {
            "name":       self.name,
            "type":       self.place_type,
            "distance_m": self.distance,
            "address":    self.address,
            "lat":        self.lat,
            "lng":        self.lng,
        }


# ─────────────────────────────────────────────────────────────────────────────
# FINDER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class NearbyPlacesFinder:
    """Google Places API se nearest safety places dhundhta hai."""

    API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
    BASE_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    # Maps our internal keys → Google Places API type strings
    TYPE_MAP: Dict[str, str] = {
        "hospital":   "hospital",
        "police":     "police",
        "mall":       "shopping_mall",
        "restaurant": "restaurant",
    }

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        """Distance in metres between two GPS coordinates."""
        R = 6_371_000
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a  = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    @classmethod
    def search_place_type(
        cls,
        latitude:   float,
        longitude:  float,
        place_type: str,       # internal key: hospital / police / mall / restaurant
        radius:     int = 2000,
    ) -> Optional[NearbyPlace]:
        """
        Ek specific place type dhundho Google Places API se.
        Nearest result return karta hai.
        """
        if not cls.API_KEY:
            print(f"❌ GOOGLE_MAPS_API_KEY not set — cannot search {place_type}")
            return None

        google_type = cls.TYPE_MAP.get(place_type.lower())
        if not google_type:
            print(f"❌ Unknown place_type: {place_type}")
            return None

        try:
            response = requests.get(
                cls.BASE_URL,
                params={
                    "location": f"{latitude},{longitude}",
                    "radius":   radius,
                    "type":     google_type,
                    "key":      cls.API_KEY,
                },
                timeout=10,
            )
            data    = response.json()
            status  = data.get("status")
            results = data.get("results", [])

            if status != "OK" or not results:
                print(f"⚠️ {place_type}: status={status}, results={len(results)}")
                return None

            # Pick the first result (Google returns closest by default with radius sort)
            best = results[0]
            loc  = best.get("geometry", {}).get("location", {})
            p_lat, p_lng = loc.get("lat"), loc.get("lng")

            if p_lat is None or p_lng is None:
                return None

            dist = cls._haversine(latitude, longitude, p_lat, p_lng)
            place = NearbyPlace(
                name       = best.get("name", place_type.title()),
                place_type = place_type.replace("_", " ").title(),
                distance   = dist,
                address    = best.get("vicinity", "Address unavailable"),
                lat        = p_lat,
                lng        = p_lng,
            )
            print(f"✅ {place_type}: {place.name} ({dist}m away)")
            return place

        except requests.Timeout:
            print(f"⏱️ Timeout searching {place_type}")
            return None
        except Exception as e:
            print(f"❌ Error searching {place_type}: {e}")
            return None

    @classmethod
    def find_all_places(
        cls,
        latitude:  float,
        longitude: float,
        radius:    int = 2000,
    ) -> Dict[str, Optional[NearbyPlace]]:
        """
        Saare 4 types (hospital, police, mall, restaurant) ek saath dhundho.
        SOS email mein include karne ke liye use hota hai.
        """
        print(f"\n🗺️ Nearby search at ({latitude:.5f}, {longitude:.5f}), radius={radius}m")
        if not cls.API_KEY:
            print("❌ API key missing — nearby places skipped")
            return {"hospital": None, "police": None, "mall": None, "restaurant": None}

        results = {}
        for key in ["hospital", "police", "mall", "restaurant"]:
            results[key] = cls.search_place_type(latitude, longitude, key, radius)

        found = sum(1 for v in results.values() if v)
        print(f"📊 Found {found}/4 place types\n")
        return results

    @classmethod
    def find_by_filter(
        cls,
        latitude:    float,
        longitude:   float,
        filter_type: str,
        radius:      int = 2000,
    ) -> Optional[NearbyPlace]:
        """
        Map filter button ke liye — specific ek type dhundho.
        filter_type: 'hospital' | 'police' | 'mall' | 'restaurant'
        """
        return cls.search_place_type(latitude, longitude, filter_type, radius)
