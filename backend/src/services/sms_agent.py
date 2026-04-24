import os
from dotenv import load_dotenv
from twilio.rest import Client

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from typing import Literal

load_dotenv()

# ── SYSTEM PROMPT ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = SystemMessage(content="""You are SheShield's Emergency Response Agent.

Your job is to alert emergency contacts via Call AND SMS on behalf of the SheShield Women's Safety App.

When given a recipient phone number, you MUST follow this exact order:

STEP 1 — CALL FIRST:
   - Write a short, clear voice script (2-3 sentences).
   - Script must start with: "This is an emergency alert from SheShield Women's Safety App."
   - Include one clear action the person must take.
   - End with: "Please respond immediately. Thank you."
   - Call 'make_call_tool' with the script.

STEP 2 — SMS AFTER CALL:
   - Wait for call tool result.
   - Then write a SHORT SMS (under 160 characters).
   - SMS must include: danger alert + one action tip + "- SheShield"
   - Call 'send_sms_tool' with the message.

RULES:
- Always call FIRST, SMS SECOND. Never skip either step.
- Do NOT explain what you are doing — just execute both steps.""")


# ── TOOL 1: CALL ───────────────────────────────────────────────────────────────
@tool
def make_call_tool(recipient_phone: str, voice_script: str) -> str:
    """Initiates an automated emergency voice call via Twilio."""

    account_sid  = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token   = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, twilio_phone]):
        return "AUTH_ERROR: Twilio credentials not configured in .env"

    try:
        client = Client(account_sid, auth_token)

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="en-IN">{voice_script}</Say>
    <Pause length="1"/>
    <Say voice="alice" language="en-IN">This alert was sent by SheShield Women Safety App. Please take immediate action.</Say>
</Response>"""

        call = client.calls.create(
            twiml=twiml,
            from_=twilio_phone,
            to=recipient_phone
        )

        return f"SUCCESS: Call initiated to {recipient_phone}. SID: {call.sid}"

    except Exception as e:
        error = str(e)
        if "authenticate" in error.lower() or "unauthorized" in error.lower():
            return "AUTH_ERROR: Invalid Twilio credentials."
        elif "not a valid phone" in error.lower() or "invalid" in error.lower():
            return "INVALID_NUMBER: Phone number format is invalid."
        elif "unable to create" in error.lower():
            return "NETWORK_ERROR: Could not connect to Twilio."
        return f"ERROR: {error}"


# ── TOOL 2: SMS ────────────────────────────────────────────────────────────────
@tool
def send_sms_tool(recipient_phone: str, message: str) -> str:
    """Sends an urgent safety SMS via Twilio after the call."""

    account_sid  = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token   = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, twilio_phone]):
        return "AUTH_ERROR: Twilio credentials not configured in .env"

    try:
        client = Client(account_sid, auth_token)

        sms = client.messages.create(
            body=message[:160],
            from_=twilio_phone,
            to=recipient_phone
        )

        return f"SUCCESS: SMS sent to {recipient_phone}. SID: {sms.sid}"

    except Exception as e:
        error = str(e)
        if "authenticate" in error.lower() or "unauthorized" in error.lower():
            return "AUTH_ERROR: Invalid Twilio credentials."
        elif "not a valid phone" in error.lower() or "invalid" in error.lower():
            return "INVALID_NUMBER: Phone number format is invalid."
        return f"ERROR: {error}"


# ── MODEL ──────────────────────────────────────────────────────────────────────
tools = [make_call_tool, send_sms_tool]

model = ChatOpenAI(
    base_url="https://api.together.xyz/v1",
    api_key=os.getenv("TOGETHER_API_KEY"),
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    temperature=0,
    timeout=30,
    max_retries=1
).bind_tools(tools)


# ── GRAPH NODES ────────────────────────────────────────────────────────────────
def call_model(state: MessagesState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def should_continue(state: MessagesState) -> Literal["tools", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# ── BUILD GRAPH ────────────────────────────────────────────────────────────────
tool_node = ToolNode(tools)

workflow = StateGraph(MessagesState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

graph = workflow.compile()


# ── RUNNER ─────────────────────────────────────────────────────────────────────
def run_emergency_agent(target_phone: str):
    user_input = f"Send an emergency alert to {target_phone}. First call, then SMS."

    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)]
    })

    all_messages = result["messages"]

    call_success = any(
        "SUCCESS" in str(msg.content) and "Call" in str(msg.content)
        for msg in all_messages
    )
    sms_success = any(
        "SUCCESS" in str(msg.content) and "SMS" in str(msg.content)
        for msg in all_messages
    )

    print("\n-- SheShield Emergency Alert Report --")

    if call_success:
        print(f"[OK] Call : Initiated to {target_phone}")
    else:
        print("[FAILED] Call")
        _print_error(all_messages)

    if sms_success:
        print(f"[OK] SMS  : Sent to {target_phone}")
    else:
        print("[FAILED] SMS")
        _print_error(all_messages)

    print("--------------------------------------\n")


def _print_error(messages):
    for msg in messages:
        content = str(msg.content)
        if "AUTH_ERROR" in content:
            print("   Reason: Auth error — check Twilio credentials in .env")
            break
        elif "NETWORK_ERROR" in content:
            print("   Reason: Network error — try again.")
            break
        elif "INVALID_NUMBER" in content:
            print("   Reason: Invalid phone number. Use +91XXXXXXXXXX format.")
            break


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TEST_PHONE = "+918318629910"
    print(f"Sending emergency alert to: {TEST_PHONE}")
    run_emergency_agent(TEST_PHONE)