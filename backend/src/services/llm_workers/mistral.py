# ─────────────────────────────────────────────────────────────────────────────
# SheShield — LLM Worker: Mistral 7B (HuggingFace Router)
# Source: LLM-Testing/mistral.py — koi change nahi, sirf import path fix kiya
# ─────────────────────────────────────────────────────────────────────────────

import httpx
from src.core.config import settings


class AISafetyService:
    API_TOKEN = settings.HUGGINGFACE_API_KEY
    API_URL   = "https://router.huggingface.co/v1/chat/completions"

    @staticmethod
    async def get_safety_report(location: str, travel_time: str, intent: str = "general"):
        if not AISafetyService.API_TOKEN:
            return "Error: API Key not found check .env file."
        if not location or len(location.strip()) < 2:
            return "Error: give correct location."

        intent_line = f"User Intent: {intent} (travel=going there, stay=staying there, return=coming back, general=safety check)"

        prompt = f"""
        You are a Women's Safety & Travel Intelligence Expert for Indian cities.

        Location: {location}
        Time: {travel_time}
        {intent_line}

        TRANSPORT RULES:
        - Mention ALL transport options that actually exist for this location.
        - For Metro: 
        * If the city has metro AND this area is on or near a metro route — mention it with timing.
        * If the city has metro BUT this area has no nearby station — write: Metro: Nearest station is far, not recommended.
        * If the city has NO metro at all — write: Metro: Not available in this city.
        - Cabs (Ola/Uber): Available in most cities, mention surge possibility at night.
        - Autos: Mention availability based on time and area type.
        - Bus: Mention if available at this hour.

        SAFETY RULES:
        - Give insights specific to THIS location only, not generic city-level advice.
        - If you have no specific data about this area, write: Limited data available for this area.
        - Base risk level on area type: market, residential, highway, isolated, etc.

        TASK:
        1. This is always a real Indian location. Give your best safety assessment.
        2. Assess safety risk based on area type and time.
        3. Give ALL confirmed transport options for this exact location.
        4. Give area-specific safety insights.
        5. Give actionable precautions.
        6. If Risk Level is Moderate or High, suggest one safer nearby area or route.

        RESPONSE FORMAT (follow this exactly, no extra lines, no extra text):

        Risk Level: [Low/Moderate/High]
        Transport Advice: [All confirmed transport options — Metro if nearby, Cabs, Autos, Bus.]
        Incident Insights: [2-3 sentences specific to this area and time. If no data: Limited data available for this area.]
        Precaution: [1-2 sentences practical and specific to this location.]
        Safe Alternative: [If Risk is Moderate or High: suggest a real safer nearby area. If Low: Not required.]
        Map Link: [If Safe Alternative exists: https://www.google.com/maps/dir/{location}/<SAFER_AREA_NAME>. If not required: Not required.]
        Emergency Contacts:
        - Women Helpline: 1090
        - Police: 100
        - Ambulance: 108

        STRICT RULES:
        - Always attempt to answer — never say location is invalid.
        - If area is unknown, write: Limited data available for this area.
        - Safe Alternative must be a real well-known area. Never make one up.
        - Map Link must use Google Maps directions format, spaces replaced with +.
        - NO markdown, NO bold text, NO bullet symbols except in Emergency Contacts.
        - NO generic advice. Every line must be location-specific.
        """

        headers = {
            "Authorization": f"Bearer {AISafetyService.API_TOKEN}",
            "Content-Type":  "application/json",
        }
        data = {
            "model":    "mistralai/Mistral-7B-Instruct-v0.2:featherless-ai",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens":  200,
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    AISafetyService.API_URL, headers=headers, json=data, timeout=15.0
                )
                response.raise_for_status()
                result = response.json()["choices"][0]["message"]["content"].strip()
            if "INVALID" in result:
                return "Location is not valid give a correct city name and landmark."
            maps_link = f"https://www.google.com/maps/search/{location.replace(' ', '+')}"
            return f"\n--- SAFETY REPORT ---\n{result}\n\nMaps: {maps_link}"
        except Exception as e:
            return f"System Error: {str(e)}"
