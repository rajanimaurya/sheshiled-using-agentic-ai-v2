# src/services/sos_agent.py
import os
import smtplib
import math
from email.message import EmailMessage
from dotenv import load_dotenv
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode

load_dotenv()

# ─────────────────────────────────────────────────────────────
#  SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = SystemMessage(content="""
You are SheShield's SOS Location Agent.

Your job is to send the user's current location to an emergency contact via email.

When you receive:
- recipient email
- latitude and longitude (or a place name)
- user name (optional)

You MUST:
1. If place name is given, first convert it to coordinates using 'geocode_place_tool'.
2. Then call 'send_location_email_tool' with the recipient, coordinates, and user name.
3. Do NOT explain anything – just execute the tool calls.
""")

# ─────────────────────────────────────────────────────────────
#  TOOL 1: Send Email
# ─────────────────────────────────────────────────────────────
@tool
def send_location_email_tool(
    recipient_email: str,
    latitude: float,
    longitude: float,
    user_name: str = "a SheShield user"
) -> str:
    """Sends an emergency email with the location and Google Maps link."""
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    if not sender_email or not sender_password:
        return "AUTH_ERROR: Email service not configured in .env"

    maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
    subject = f"SOS ALERT: {user_name} needs immediate help"
    body = f"""
Dear Safety Contact,

This is an automated SOS alert from the SheShield Women's Safety App.

{user_name} has triggered the SOS button. Their current location is:

📍 Coordinates: {latitude}, {longitude}

🔗 View on Google Maps: {maps_link}

Please check on them immediately.

—
SheShield Safety Team
    """.strip()

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipient_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)

        return f"SUCCESS: SOS location email sent to {recipient_email}"
    except Exception as e:
        return f"ERROR: {str(e)}"

# ─────────────────────────────────────────────────────────────
#  TOOL 2: Geocode (place name → coordinates) using Google Maps API
# ─────────────────────────────────────────────────────────────
@tool
def geocode_place_tool(place_name: str) -> str:
    """
    Converts a place name or address to latitude,longitude.
    Uses Google Maps Geocoding API (more accurate than Nominatim).
    Returns a string like "lat,lon" or an error.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "ERROR: Google Maps API key missing"

    import requests
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": place_name, "key": api_key}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            lat = loc["lat"]
            lng = loc["lng"]
            return f"{lat},{lng}"
        else:
            return f"ERROR: Geocoding failed - {data['status']}"
    except Exception as e:
        return f"ERROR: {str(e)}"

# ─────────────────────────────────────────────────────────────
#  MODEL & TOOLS
# ─────────────────────────────────────────────────────────────
tools = [send_location_email_tool, geocode_place_tool]

model = ChatOpenAI(
    base_url="https://api.together.xyz/v1",
    api_key=os.getenv("TOGETHER_API_KEY"),
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    temperature=0,
    timeout=30
).bind_tools(tools)

# ─────────────────────────────────────────────────────────────
#  GRAPH NODES
# ─────────────────────────────────────────────────────────────
def call_model(state: MessagesState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: MessagesState) -> Literal["tools", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

tool_node = ToolNode(tools)
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")
graph = workflow.compile()

# ─────────────────────────────────────────────────────────────
#  PUBLIC ASYNC FUNCTION (to call from FastAPI)
# ─────────────────────────────────────────────────────────────
async def send_sos_email_agent(recipient_email: str, lat: float, lon: float, user_name: str = ""):
    """
    Direct GPS-based SOS email using LangGraph agent.
    This will call the 'send_location_email_tool' via the agent.
    """
    user_input = f"Send SOS location to {recipient_email}. Latitude {lat}, Longitude {lon}. User name: {user_name if user_name else 'a SheShield user'}."
    result = graph.invoke({"messages": [HumanMessage(content=user_input)]})
    all_messages = result["messages"]
    success = any("SUCCESS" in str(msg.content) for msg in all_messages)
    if success:
        return True, f"Email sent to {recipient_email}"
    else:
        error = next((str(msg.content) for msg in all_messages if "ERROR" in str(msg.content)), "Unknown error")
        return False, error

async def send_sos_by_place_agent(recipient_email: str, place_name: str, user_name: str = ""):
    """
    Place name based SOS email using LangGraph agent.
    Agent will call geocode tool first, then email tool.
    """
    user_input = f"Send SOS location to {recipient_email}. Place name: {place_name}. User name: {user_name if user_name else 'a SheShield user'}."
    result = graph.invoke({"messages": [HumanMessage(content=user_input)]})
    all_messages = result["messages"]
    success = any("SUCCESS" in str(msg.content) for msg in all_messages)
    if success:
        return True, f"Email sent to {recipient_email} for location '{place_name}'"
    else:
        error = next((str(msg.content) for msg in all_messages if "ERROR" in str(msg.content)), "Unknown error")
        return False, error