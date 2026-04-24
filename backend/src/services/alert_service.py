# ─────────────────────────────────────────────────────────────────────────────
# SheShield — Alert Dispatcher Service
#
# Flow:
#   1. Emergency action is triggered
#   2. For each contact:
#        • If phone exists  → Send SMS + Call via sms_agent
#        • If email exists  → Send Email via email_agent
#   3. Caller is responsible for database logging
#
# Note:
#   sms_agent.py and email_agent.py remain unchanged.
#   This service safely executes them in FastAPI's async environment.
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
from typing import List, Dict, Any


async def dispatch_alerts(
    contacts: List[Any],
    user_name: str = "",
    location: str = "",
    nearby_places: dict = None
) -> Dict[str, Any]:
    """
    Dispatch emergency alerts to all provided contacts in parallel.

    Args:
        contacts (List[Any]): List of contact objects or dicts
                              Expected fields: name, phone, email
        user_name (str): Name of the user in distress (optional)
        location (str): Location info (optional)
        nearby_places (dict): Nearby places info (optional)

    Returns:
        Dict[str, Any]: Summary of alerts sent
            {
                "sms_call_sent": int,
                "email_sent": int,
                "errors": List[str]
            }
    """

    # Lazy imports to avoid unnecessary loading at startup
    from src.services.sms_agent import run_emergency_agent
    from src.services.direct_sos_emailer import DirectSOSEmailer

    tasks = []
    task_metadata = []

    loop = asyncio.get_running_loop()  # modern & safe

    for contact in contacts:
        # Support both dict and object (e.g., ORM models)
        phone = contact.get("phone") if isinstance(contact, dict) else getattr(contact, "phone", None)
        email = contact.get("email") if isinstance(contact, dict) else getattr(contact, "email", None)

        if phone:
            tasks.append(
                loop.run_in_executor(None, run_emergency_agent, phone)
            )
            task_metadata.append(("sms_call", phone))

        if email:
            # Use direct emailer (more reliable than LangGraph)
            def send_email_task():
                result = DirectSOSEmailer.send_sos_email(
                    recipient_email=email,
                    user_name=user_name,
                    location=location,
                    nearby_places=nearby_places
                )
                return result
            
            tasks.append(
                loop.run_in_executor(None, send_email_task)
            )
            task_metadata.append(("email", email))

    if not tasks:
        return {
            "sms_call_sent": 0,
            "email_sent": 0,
            "errors": ["No valid contacts found"]
        }

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    sms_call_sent = 0
    email_sent = 0
    errors = []

    for (task_type, target), result in zip(task_metadata, results):
        if isinstance(result, Exception):
            errors.append(f"{task_type} to {target} failed: {str(result)}")
        else:
            if task_type == "sms_call":
                sms_call_sent += 1
            elif task_type == "email":
                # Check if email was successful
                if isinstance(result, dict) and result.get("success"):
                    email_sent += 1
                else:
                    errors.append(f"email to {target}: {result.get('message', 'Unknown error')}")

    return {
        "sms_call_sent": sms_call_sent,
        "email_sent": email_sent,
        "errors": errors
    }