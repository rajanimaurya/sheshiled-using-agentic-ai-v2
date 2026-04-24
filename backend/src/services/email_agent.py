import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from typing import Literal

load_dotenv()

#  SYSTEM PROMPT 
SYSTEM_PROMPT = SystemMessage(content="""You are SheShield's professional Email Writing Agent.

Your job is to write and send safety emails on behalf of the SheShield Women's Safety App.

When given a recipient email, you MUST:
1. Write a professional, warm, and empathetic email.
2. Subject should be clear and relevant to women's safety.
3. Body should include:
   - A proper greeting (Dear User)
   - A clear safety message or alert.
   - Actionable safety tips (e.g., share live location, use SOS features).
   - Encouraging closing line.
   - Signature: "Warm regards, SheShield Safety Team"
4. Call 'send_email_tool' immediately with the composed subject and body.
5. Do NOT explain what you are doing — just write and send the email.""")


# TOOL
@tool
def send_email_tool(recipient_email: str, subject: str, body: str) -> str:
    """Sends a professional safety email to the given recipient."""

    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    if not sender_email or not sender_password:
        return "AUTH_ERROR: Email service not configured."

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)

        return f"SUCCESS: Mail sent successfully to {recipient_email}"

    except smtplib.SMTPAuthenticationError:
        return "AUTH_ERROR: Incorrect Email or App Password."
    except smtplib.SMTPConnectError:
        return "NETWORK_ERROR: Could not connect to the server."
    except smtplib.SMTPRecipientsRefused:
        return "INVALID_EMAIL: Recipient email address is invalid."
    except Exception as e:
        return f"ERROR: {str(e)}"


# MODEL 
tools = [send_email_tool]

model = ChatOpenAI(
    base_url="https://api.together.xyz/v1",
    api_key=os.getenv("TOGETHER_API_KEY"),
    model="deepseek-ai/DeepSeek-V3",
    temperature=0
).bind_tools(tools)


# GRAPH NODE
def call_model(state: MessagesState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}


def should_continue(state: MessagesState) -> Literal["tools", END]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


#  BUILD GRAPH 
tool_node = ToolNode(tools)

workflow = StateGraph(MessagesState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

graph = workflow.compile()


def run_email_agent(target_email: str):
    user_input = f"Send a professional women's safety email to {target_email}."

    result = graph.invoke({
        "messages": [HumanMessage(content=user_input)]
    })

    
    all_messages = result["messages"]
    sent = any("SUCCESS" in str(msg.content) for msg in all_messages)

    if sent:
        print(f" Email sent successfully to {target_email}!")
    else:
        for msg in all_messages:
            content = str(msg.content)
            if "NETWORK_ERROR" in content:
                print(" Network error — please try again.")
                break
            elif "AUTH_ERROR" in content:
                print("Auth error — check .env file.")
                break
            elif "INVALID_EMAIL" in content:
                print("Invalid email address.")
                break
        else:
            print("Something went wrong.")



if __name__ == "__main__":
    email_id = input("Enter recipient email ID: ")
    run_email_agent(email_id)