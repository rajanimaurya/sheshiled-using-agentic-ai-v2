#!/usr/bin/env python3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class DirectSOSEmailer:
    SENDER_EMAIL = os.getenv("EMAIL_USER")
    SENDER_PASSWORD = os.getenv("EMAIL_PASS")

    @staticmethod
    def send_sos_email(recipient_email, user_name="User", location="Unknown", nearby_places=None):
        if not DirectSOSEmailer.SENDER_EMAIL or not DirectSOSEmailer.SENDER_PASSWORD:
            return {"success": False, "message": "Email credentials not configured"}
        try:
            subject = f"SOS ALERT from {user_name}"
            body = f"EMERGENCY! {user_name} needs help!\nLocation: {location}\nhttps://maps.google.com?q={location}"
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = DirectSOSEmailer.SENDER_EMAIL
            msg["To"] = recipient_email
            msg.attach(MIMEText(body, "plain"))
            print(f"📧 Sending email to {recipient_email}...")
            with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                smtp.starttls()
                smtp.login(DirectSOSEmailer.SENDER_EMAIL, DirectSOSEmailer.SENDER_PASSWORD)
                smtp.send_message(msg)
            print(f"✅ Email sent to {recipient_email}")
            return {"success": True, "message": f"Email sent to {recipient_email}"}
        except Exception as e:
            print(f"❌ Email error: {str(e)}")
            return {"success": False, "message": str(e)}
