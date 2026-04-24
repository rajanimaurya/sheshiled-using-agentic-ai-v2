import os
import math
import asyncio
import requests
from dotenv import load_dotenv
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode

load_dotenv()


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = SystemMessage(content="""
You are SheShield's professional Nearby Places Agent.

Your task is to find the nearest safety-critical places for a user in need.

Instructions:
1. Always call 'find_nearby_places_tool' with given coordinates and radius (default 500m).
2. Extract and present:
   - Nearest Hospital
   - Nearest Police Station
   - Nearest Mall / Market
   - Nearest Restaurant
3. For each place include:
   - Name
   - Type
   - Distance (in metres)
   - Address (if available)
4. If no places are found, clearly suggest increasing the radius.
5. End response with: "Stay safe. — SheShield Safety Team"
6. Do NOT explain internal steps.
""")


# ─────────────────────────────────────────────
# HELPER — Haversine Distance
# ─────────────────────────────────────────────
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate distance in metres between two GPS coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


# ─────────────────────────────────────────────
# TOOL — Fetch data from Google Places API
# ─────────────────────────────────────────────
@tool
def find_nearby_places_tool(latitude: float, longitude: float, radius_metres: int = 500) -> str:
    """
    Fetch nearest hospital, police station, mall, and restaurant
    using Google Places Nearby Search API.
    """

    GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

    if not GOOGLE_API_KEY:
        return "❌ GOOGLE_MAPS_API_KEY not found in environment. Please add it to your .env file."

    NEARBY_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    CATEGORIES = {
        "hospital": {
            "type": "hospital",
            "label": "Hospital",
            "icon": "🏥"
        },
        "police": {
            "type": "police",
            "label": "Police Station",
            "icon": "🚔"
        },
        "mall": {
            "type": "shopping_mall",
            "label": "Mall / Market",
            "icon": "🏬"
        },
        "restaurant": {
            "type": "restaurant",
            "label": "Restaurant",
            "icon": "🍽️"
        },
    }

    results = {}

    for key, meta in CATEGORIES.items():
        params = {
            "location": f"{latitude},{longitude}",
            "radius": radius_metres,
            "type": meta["type"],
            "key": GOOGLE_API_KEY,
        }

        try:
            response = requests.get(NEARBY_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            status = data.get("status")

            if status == "REQUEST_DENIED":
                results[key] = {"error": "API key invalid or Places API not enabled."}
                continue

            if status == "OVER_QUERY_LIMIT":
                results[key] = {"error": "API quota exceeded. Try again later."}
                continue

            places_raw = data.get("results", [])

            if not places_raw:
                results[key] = None
                continue

            # Calculate distances and find nearest
            places = []
            for place in places_raw:
                loc = place.get("geometry", {}).get("location", {})
                p_lat = loc.get("lat")
                p_lng = loc.get("lng")

                if not p_lat or not p_lng:
                    continue

                dist = haversine_distance(latitude, longitude, p_lat, p_lng)

                places.append({
                    "name": place.get("name", meta["label"]),
                    "type": meta["label"],
                    "dist_m": dist,
                    "address": place.get("vicinity", "Address unavailable"),
                    "rating": place.get("rating", None),
                    "open_now": place.get("opening_hours", {}).get("open_now", None),
                })

            # Sort by distance
            places = sorted(places, key=lambda x: x["dist_m"])
            results[key] = places[0] if places else None

        except requests.exceptions.Timeout:
            results[key] = {"error": "Request timed out. Check internet connection."}
        except requests.exceptions.ConnectionError:
            results[key] = {"error": "Connection failed. Check internet."}
        except requests.exceptions.RequestException as e:
            results[key] = {"error": f"Request failed: {str(e)}"}

    # ─────────────────────────────────────────────
    # Format Output
    # ─────────────────────────────────────────────
    lines = [f"\n📍 Nearby Places within {radius_metres}m:\n"]
    found_any = False

    for key, meta in CATEGORIES.items():
        place = results.get(key)
        lines.append(f"{meta['icon']} {meta['label']}:")

        if place is None:
            lines.append("   • Not found in this radius")
        elif "error" in place:
            lines.append(f"   • ⚠️ {place['error']}")
        else:
            found_any = True
            lines.append(f"   • {place['name']}")
            lines.append(f"     📏 {place['dist_m']}m away")
            lines.append(f"     📍 {place['address']}")

            if place["rating"]:
                lines.append(f"     ⭐ Rating: {place['rating']}")

            if place["open_now"] is True:
                lines.append("     🟢 Open Now")
            elif place["open_now"] is False:
                lines.append("     🔴 Closed Now")

        lines.append("")

    if not found_any:
        lines.append("⚠️ No places found in this radius.")
        lines.append("💡 Try increasing the search radius (e.g., 1000m, 2000m).")

    lines.append("Stay safe. — SheShield Safety Team")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# MODEL + TOOL BINDING
# ─────────────────────────────────────────────
_tools = [find_nearby_places_tool]

_model = ChatOpenAI(
    base_url="https://api.together.xyz/v1",
    api_key=os.getenv("TOGETHER_API_KEY"),
    model="deepseek-ai/DeepSeek-V3",
    temperature=0
).bind_tools(_tools)


# ─────────────────────────────────────────────
# GRAPH NODES
# ─────────────────────────────────────────────
def _call_model(state: MessagesState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = _model.invoke(messages)
    return {"messages": [response]}


def _should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    return "tools" if last.tool_calls else "__end__"


# ─────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────
_tool_node = ToolNode(_tools)

_workflow = StateGraph(MessagesState)
_workflow.add_node("agent", _call_model)
_workflow.add_node("tools", _tool_node)

_workflow.add_edge(START, "agent")
_workflow.add_conditional_edges("agent", _should_continue)
_workflow.add_edge("tools", "agent")

_graph = _workflow.compile()


# ─────────────────────────────────────────────
# PUBLIC FUNCTION
# ─────────────────────────────────────────────
async def run_nearby_agent(latitude: float, longitude: float, radius: int = 500) -> str:
    """
    Main entry point for Nearby Places Agent.
    Uses Google Maps Places API for accurate results in India.

    Returns:
        str: Final formatted response from the agent.
    """
    user_input = (
        f"Find nearest hospital, police station, mall, and restaurant "
        f"within {radius} metres of latitude {latitude}, longitude {longitude}."
    )

    loop = asyncio.get_running_loop()

    result = await loop.run_in_executor(
        None,
        lambda: _graph.invoke({"messages": [HumanMessage(content=user_input)]})
    )

    # Extract final response (ignore tool messages)
    for msg in reversed(result["messages"]):
        content = getattr(msg, "content", "")
        tool_calls = getattr(msg, "tool_calls", [])

        if content and not tool_calls:
            return content

    return "Unable to fetch nearby places. Please try again."