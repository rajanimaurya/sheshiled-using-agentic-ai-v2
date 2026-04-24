# ─────────────────────────────────────────────────────────────────────────────
# SheShield — AI Safety Service
#
# Flow:
#   get_safety_report(location, time, intent)
#       ↓
#   5 LLM Workers parallel (llama, qwen, gemma, mistral, openai)
#       ↓
#   DeepSeek Judge → structured JSON verdict
#       ↓
#   Structured response return
#
# log_activity() → Database mein safety check save karo
#
# NOTE: Original ai_service.py ka single-model approach replace hua hai.
#       Pehla version sirf Llama use karta tha.
#       Ab sare 5 workers + judge pipeline use hoti hai (LLM-Testing se).
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.llm_workers import MODELS
from src.services.judge_service import call_judge


# ── Individual worker runner — 3 retries ─────────────────────────────────────
async def _run_worker(name: str, location: str, time: str, intent: str = "general"):
    """Ek LLM worker chalao, 3 bar try karo fail hone par."""
    for attempt in range(3):
        try:
            result = await MODELS[name].AISafetyService.get_safety_report(location, time, intent)
            return name, (result or "").strip()
        except Exception as e:
            if attempt == 2:
                return name, f"ERROR: {e}"
            await asyncio.sleep(1.5)


# ── Main AI Safety Service ────────────────────────────────────────────────────
class AISafetyService:

    @staticmethod
    async def get_safety_report(
        location: str,
        travel_time: str,
        intent: str = "general",
    ) -> dict:
        """
        Pura ensemble pipeline chalao aur structured dict return karo.

        Returns dict with keys:
            status, risk_level, summary, transport, precaution,
            safe_alternative, confidence_score, maps_link,
            maps_directions, emergency_contacts
        """
        # ── Input validation ─────────────────────────────────────────────────
        if not location or len(location.strip()) < 2:
            return {
                "status":  "error",
                "message": "Location bahut chhota hai. Thoda detail mein likho.",
            }
        if location.strip().isdigit():
            return {
                "status":  "error",
                "message": "Numbers valid location nahi hain.",
            }

        # ── Step 1: 5 workers parallel chalao ────────────────────────────────
        raw_results = await asyncio.gather(
            *(_run_worker(name, location, travel_time, intent) for name in MODELS)
        )
        worker_outputs = dict(raw_results)

        # ── Step 2: Judge se final verdict lo ────────────────────────────────
        judge_response = await call_judge(location, travel_time, worker_outputs)

        # ── Step 3: Judge fail → best worker se fallback ─────────────────────
        if judge_response.get("status") != "success":
            valid = {
                k: v for k, v in worker_outputs.items()
                if not str(v).startswith("ERROR:")
            }
            fallback_text = next(
                iter(valid.values()),
                "Report generate nahi ho saka. Dobara try karein."
            )
            return {
                "status":           "fallback",
                "risk_level":       "Unknown",
                "summary":          fallback_text,
                "transport":        "—",
                "precaution":       "—",
                "safe_alternative": "Not required",
                "confidence_score": 0,
                "maps_link":        f"https://www.google.com/maps/search/{location.replace(' ', '+')}",
                "maps_directions":  None,
                "emergency_contacts": {
                    "women_helpline": "1090",
                    "police":         "100",
                    "ambulance":      "108",
                },
            }

        # ── Step 4: Final structured response banao ───────────────────────────
        v        = judge_response["result"]
        safe_alt = v.get("safe_alternative", "Not required")

        maps_search = f"https://www.google.com/maps/search/{location.replace(' ', '+')}"
        maps_dir    = None
        if safe_alt and safe_alt.lower() not in ("not required", ""):
            maps_dir = (
                f"https://www.google.com/maps/dir/"
                f"{location.replace(' ', '+')}/{safe_alt.replace(' ', '+')}"
            )

        return {
            "status":           "success",
            "risk_level":       v.get("risk_level", "Unknown"),
            "summary":          v.get("summary", ""),
            "transport":        v.get("transport", ""),
            "precaution":       v.get("precaution", ""),
            "safe_alternative": safe_alt,
            "confidence_score": v.get("confidence_score", 0),
            "maps_link":        maps_search,
            "maps_directions":  maps_dir,
            "emergency_contacts": {
                "women_helpline": "1090",
                "police":         "100",
                "ambulance":      "108",
            },
        }

    @staticmethod
    async def log_activity(
        db: AsyncSession,
        user_id: int,
        location: str,
        time: str,
        report: dict,
    ):
        """Safety check ko database mein save karo."""
        from src.models.ai_log import AIActivityLog

        # Risk level validate karo — sirf valid values hi save karo
        risk = report.get("risk_level", "Unknown")
        if risk not in ("Low", "Moderate", "High"):
            risk = "Unknown"

        new_log = AIActivityLog(
            user_id=user_id,
            location=location,
            travel_time=time,
            risk_level=risk,
        )
        db.add(new_log)
        await db.commit()
        await db.refresh(new_log)
        return new_log
