# ─────────────────────────────────────────────────────────────────────────────
# SheShield — LLM Worker Registry
# Saare 5 workers yahan register hote hain.
# ai_service.py aur judge_service.py inhe import karte hain.
# ─────────────────────────────────────────────────────────────────────────────

from src.services.llm_workers import lliama, qwen, google_gemma, mistral, openai_worker

# Model name → module mapping
# Har module mein ek AISafetyService class honi chahiye
# jisme get_safety_report(location, travel_time, intent) method ho
MODELS = {
    "llama":   lliama,
    "qwen":    qwen,
    "gemma":   google_gemma,
    "mistral": mistral,
    "openai":  openai_worker,
}
