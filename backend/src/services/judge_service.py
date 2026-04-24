# ─────────────────────────────────────────────────────────────────────────────
# SheShield — Judge Service (DeepSeek V3)
# 5 LLM workers output used by judge and give the final ans.

# ─────────────────────────────────────────────────────────────────────────────

import re
import json
import asyncio
import httpx
from src.core.config import settings

JUDGE_API_URL = "https://api.together.xyz/v1/chat/completions"
JUDGE_MODEL   = "deepseek-ai/DeepSeek-V3"


async def call_judge(location: str, time: str, outputs: dict) -> dict:
    """
    5 LLM worker outputs leke ek final JSON verdict deta hai.

    Returns:
        { "status": "success", "result": { risk_level, summary, transport,
          precaution, safe_alternative, confidence_score } }
        ya
        { "status": "failed", "reason": "..." }
    """
    judge_key = settings.TOGETHER_API_KEY
    if not judge_key:
        return {"status": "skipped", "reason": "TOGETHER_API_KEY missing"}

    # Sirf valid outputs bhejo judge ko
    valid_outputs = {k: v for k, v in outputs.items() if v and not str(v).startswith("ERROR:")}

    if len(valid_outputs) < 2:
        return {"status": "failed", "reason": "Not enough valid model outputs"}

    prompt = f"""
        You are an expert Safety Auditor for Indian cities acting as an AI Judge.

        Location: {location}
        Time: {time}

        Below are answers from multiple AI models. Each model may explain things in a different style.

        MODEL OUTPUTS:
        {json.dumps(valid_outputs, indent=2, ensure_ascii=False)}

        YOUR TASK

        A normal user may become confused after reading multiple answers.
        Your job is to carefully analyze all responses and produce ONE clear safety recommendation.

        Evaluation process:

        1. Carefully read each response and understand its meaning. Focus on the safety implication rather than the exact wording.

        2. For every response, determine what it suggests about safety:
        - Safe
        - Not Safe
        - Mixed / Uncertain

        3. Compare all responses and identify the majority opinion across them.

        4. Re-verify the majority decision by checking whether those responses sound realistic for the given location and time.

        5. If any response contains exaggerated, unrealistic, or unsupported information, treat it as unreliable and reduce its importance.

        6. Combine the most reliable insights from the responses and generate ONE final safety recommendation.

        IMPORTANT:

        The final answer must be simple and understandable for a non-technical person.

        Do NOT mention AI models, analysis steps, or judging process in the final answer.

        Risk Level Meaning:

        Low - Well-known safe area, daytime or early evening (before 9 PM), good lighting, busy streets, metro/cab available.

        Moderate - Mixed safety signals — late evening (9 PM-12 AM), some dark areas, limited transport, occasional crime reports.

        High - Known dangerous area OR very late night (after 12 AM) OR isolated location with no transport.

        IMPORTANT: Do NOT default to Moderate. If the area is genuinely safe at that time, return Low.

        STRICT RULES:
        - Return ONLY valid JSON
        - risk_level must be exactly: Low, Moderate, High
        - confidence_score must be an integer between 0 and 100

        Return ONLY this JSON:

        {{
        "risk_level": "Low/Moderate/High",
        "summary": "2-3 simple sentences explaining the safety situation.",
        "transport": "Common transport options available at this time.",
        "precaution": "1-2 simple safety tips.",
        "safe_alternative": "One short area name only, max 3 words. Example: Bandra West, Assi Ghat. No sentences. If Low return 'Not required'.",
        "confidence_score": 0
        }}
        """.strip()

    for attempt in range(5):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    JUDGE_API_URL,
                    headers={
                        "Authorization": f"Bearer {judge_key}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model":    JUDGE_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens":  500,
                    },
                )
                resp.raise_for_status()
                raw = re.sub(
                    r"```json|```", "",
                    resp.json()["choices"][0]["message"]["content"]
                ).strip()

            # JSON parse karo — fallback with regex agar extra text ho
            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if not match:
                    raise ValueError("Judge response is not valid JSON")
                result = json.loads(match.group(0))

            # Confidence score normalize karo
            score = result.get("confidence_score", 0)
            try:
                score = int(score * 100) if isinstance(score, float) and score <= 1 else int(score)
            except (ValueError, TypeError):
                score = 0
            result["confidence_score"] = max(0, min(score, 100))

            return {"status": "success", "result": result}

        except Exception as e:
            if attempt == 2:
                return {"status": "failed", "reason": str(e)}
            await asyncio.sleep(2)

    return {"status": "failed", "reason": "Judge exhausted all retries"}
