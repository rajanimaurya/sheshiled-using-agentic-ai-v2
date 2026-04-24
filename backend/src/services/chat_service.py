# ─────────────────────────────────────────────────────────────────────────────
# SheShield — Chat Service
#
# Source: LLM-Testing/judge_deepseek.py → chat_with_ai() function
# Changes:
#   - dotenv → src.core.config.settings se API key lega
#   - httpx timeout thoda badha (network ke liye)
#   - Structured return type consistent rakha
#
# Flow:
#   chat_with_ai(history) → LLM se location/time extract karo
#       → ready=True hone par → ai_service.py pipeline trigger hoti hai (router se)
#       → ready=False hone par → sirf reply return karo (next turn ka wait)
# ─────────────────────────────────────────────────────────────────────────────

import re
import json
import httpx

from src.core.config import settings

JUDGE_API_URL = "https://api.together.xyz/v1/chat/completions"
JUDGE_MODEL   = "deepseek-ai/DeepSeek-V3"


async def chat_with_ai(history: list) -> dict:
    """
    Conversation history leke location, time, intent extract karo.

    Args:
        history: List of {"role": "user"/"assistant", "content": "..."} dicts

    Returns:
        {
            "location": str | None,
            "time":     str,          # "Not specified" if missing
            "intent":   str,          # travel/stay/return/general
            "ready":    bool,         # True sirf tab jab dono location+time ho
            "reply":    str           # AI ka natural reply
        }
    """
    prompt = f"""You are an Indian women safety assistant. Be friendly — like a close friend.

        STRICT LANGUAGE RULE: Detect the language of the user's LATEST message and reply in EXACTLY that language. No mixing.
        - If latest message is in English → reply in English ONLY
        - If latest message is in Hinglish → reply in Hinglish ONLY  
        - If latest message is in Hindi → reply in Hindi ONLY
        Do NOT mix languages under any circumstance.

        STRICT SCOPE RULE — NON NEGOTIABLE:
            - You are ONLY a women safety assistant. Nothing else.
            - You ONLY respond to: greetings, location names, travel time, safety queries, transport questions
            - Greetings like "hi", "hello", "how are you", "good morning" → respond warmly and redirect to safety topic
            - If user asks ANYTHING outside safety topic (politics, celebrities, jokes, coding, recipes, news, sports etc.) → do NOT answer, just redirect friendly
            - Rejection reply must be short, friendly, and always bring back to safety topic

        Conversation history:
        {json.dumps(history, ensure_ascii=False)}
        
        TIME RULE: Convert time to proper 12-hour format:
        - "raat" / "night" / "PM" → add PM  (e.g. "raat 9 baje" → "9:00 PM")
        - "subah" / "morning" / "AM" → add AM  (e.g. "subah 6 baje" → "6:00 AM")
        - "dopahar" / "afternoon" → PM
        - "shaam" / "evening" → PM
        - Always return time as "H:MM AM/PM" format, never as "9 bje" or "9 baje"
       
        Your job:
        1. First understand what the user is saying — is it a greeting, a safety query, or something else.
        2. Respond naturally — if they say "hi" then warmly greet them and ask where they want to go.
        If they give a location, ask for the time. If both are given, set ready to true.
        3. Never be robotic — give a fresh natural reply based on context every time.
        
        LOCATION RULE:
         - Only accept real Indian place names — cities, areas, landmarks, markets, railway stations
         - If location looks fake or random (e.g. "xyz", "abc", "test", single letters, nonsense) → set location as null, do NOT set ready true, ask for a real location naturally

        Extract from the full conversation:
        - location — null if not found
        - time — "Not specified" if not found
        - intent — travel/stay/return/general
        - ready — true ONLY if BOTH location and time are clearly found
        - reply — always a natural friendly reply (1-2 lines max)

        Return ONLY valid JSON:
        {{"location": null, "time": "Not specified", "intent": "general", "ready": false, "reply": ".."}}"""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                JUDGE_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model":       JUDGE_MODEL,
                    "messages":    [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens":  150,
                },
            )
            resp.raise_for_status()

        raw = re.sub(
            r"```json|```", "",
            resp.json()["choices"][0]["message"]["content"]
        ).strip()

        result = json.loads(raw)
        return result

    except Exception:
        # Graceful fallback — pipeline rok do, user se dobara pucho
        return {
            "location": None,
            "time":     "Not specified",
            "intent":   "general",
            "ready":    False,
            "reply":    "tell me, where are you going? 😊",
        }