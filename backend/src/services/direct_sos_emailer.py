#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
# SHESHIELD - DIRECT SOS EMAIL SENDER (Simple & Working!)
# ─────────────────────────────────────────────────────────────────────────────

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


class DirectSOSEmailer:
    """Direct email sender - bypasses LangGraph complexity"""
    
    SENDER_EMAIL = os.getenv("EMAIL_USER")
    SENDER_PASSWORD = os.getenv("EMAIL_PASS")
    
    @staticmethod
    def send_sos_email(
        recipient_email: str,
        user_name: str = "User",
        location: str = "Unknown",
        nearby_places: dict = None
    ) -> dict:
        """
        Send direct SOS email
        
        Args:
            recipient_email: Email to send to
            user_name: Name of person in distress
            location: GPS location string
            nearby_places: Dict of nearby safe places
        
        Returns:
            {"success": bool, "message": str}
        """
        
        if not DirectSOSEmailer.SENDER_EMAIL or not DirectSOSEmailer.SENDER_PASSWORD:
            return {
                "success": False,
                "message": "❌ Email credentials not configured in .env"
            }
        
        try:
            # Create HTML email
            subject = f"🚨 URGENT: SOS Alert from {user_name}"
            
            html_body = DirectSOSEmailer._create_sos_html(
                user_name, location, nearby_places
            )
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = DirectSOSEmailer.SENDER_EMAIL
            msg["To"] = recipient_email
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            
            # Attach HTML
            msg.attach(MIMEText(html_body, "html"))
            
            # Send via Gmail SMTP
            print(f"📧 Sending SOS email to {recipient_email}...")
            
            with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                smtp.starttls()
                smtp.login(DirectSOSEmailer.SENDER_EMAIL, DirectSOSEmailer.SENDER_PASSWORD)
                smtp.send_message(msg)
            
            message = f"✅ SOS email sent to {recipient_email}"
            print(message)
            
            return {
                "success": True,
                "message": message,
                "recipient": recipient_email
            }
            
        except smtplib.SMTPAuthenticationError as e:
            message = "❌ AUTH ERROR: Wrong email or app password"
            print(message)
            return {"success": False, "message": message, "error": str(e)}
            
        except smtplib.SMTPConnectError as e:
            message = "❌ NETWORK ERROR: Could not connect to Gmail"
            print(message)
            return {"success": False, "message": message, "error": str(e)}
            
        except Exception as e:
            message = f"❌ ERROR: {str(e)}"
            print(message)
            return {"success": False, "message": message, "error": str(e)}
    
    @staticmethod
    def _create_sos_html(user_name, location, nearby_places=None):
        """Create beautiful SOS HTML email"""
        
        nearby_html = ""
        if nearby_places:
            for place_type, place in nearby_places.items():
                if place:
                    icon_map = {
                        "police": "🚔",
                        "hospital": "🏥",
                        "mall": "🏬",
                        "restaurant": "🍽️"
                    }
                    icon = icon_map.get(place_type, "📍")
                    
                    # Handle both dict and object formats
                    name = place.get("name") if isinstance(place, dict) else getattr(place, "name", "Unknown")
                    distance = place.get("distance_m") if isinstance(place, dict) else getattr(place, "distance_m", 0)
                    address = place.get("address") if isinstance(place, dict) else getattr(place, "address", "N/A")
                    
                    nearby_html += f"""
                    <tr>
                        <td style="padding: 12px; border-bottom: 1px solid #e0e0e0;">
                            <strong>{icon} {place_type.upper()}</strong><br>
                            {name}<br>
                            <span style="color: #ff0000; font-weight: bold;">📏 {distance}m away</span><br>
                            <small style="color: #666;">{address}</small>
                        </td>
                    </tr>
                    """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff6b6b 0%, #d63031 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
                .content {{ background: white; padding: 20px; margin: 15px 0; border-radius: 8px; }}
                .alert-box {{ background: #ffe0e0; border-left: 4px solid #ff0000; padding: 15px; margin: 15px 0; }}
                .location-box {{ background: #e8f4f8; padding: 15px; border-left: 4px solid #007AFF; margin: 15px 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                .button {{ display: inline-block; background: #ff6b6b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
                .footer {{ background: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">🚨 SOS EMERGENCY ALERT</h1>
                    <p style="margin: 5px 0;">IMMEDIATE HELP NEEDED</p>
                </div>
                
                <div class="content">
                    <p>Dear Safety Contact,</p>
                    
                    <div class="alert-box">
                        <strong>⚠️ EMERGENCY ALERT</strong><br>
                        <strong>{user_name}</strong> has triggered the SOS emergency button and needs immediate assistance!
                    </div>
                    
                    <div class="location-box">
                        <strong>📍 Current Location:</strong><br>
                        {location}<br>
                        <a href="https://www.google.com/maps/search/?api=1&query={location}" target="_blank" class="button">
                            🗺️ View on Google Maps
                        </a>
                    </div>
                    
                    <h3>🆘 Nearest Safe Places:</h3>
                    <table>
                        {nearby_html if nearby_html else '<tr><td style="padding: 12px; color: #999;">Searching for nearby places...</td></tr>'}
                    </table>
                    
                    <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;">
                        <strong>✅ Actions Taken:</strong><br>
                        ✓ Local police have been alerted<br>
                        ✓ Your location has been shared<br>
                        ✓ Nearby safe places identified<br>
                        ✓ Emergency contacts notified
                    </div>
                    
                    <h4>📞 Emergency Numbers (India):</h4>
                    <ul>
                        <li><strong>Police Emergency:</strong> 100</li>
                        <li><strong>Women's Helpline:</strong> 1091</li>
                        <li><strong>Ambulance:</strong> 102</li>
                        <li><strong>Childline:</strong> 1098</li>
                    </ul>
                    
                    <p style="color: #666; font-size: 13px;">
                        <strong>Note:</strong> This is an automated alert from SheShield Women's Safety App.
                        Please reach out to {user_name} immediately to ensure their safety.
                    </p>
                </div>
                
                <div class="footer">
                    <strong>SheShield - Women's Safety App</strong><br>
                    Protecting women through technology and awareness
                </div>
            </div>
        </body>
        </html>
        """
        
        return html


# Test function
def test_email():
    """Test email sending"""
    print("🧪 Testing direct email sender...")
    
    result = DirectSOSEmailer.send_sos_email(
        recipient_email="test@gmail.com",  # Change this!
        user_name="Test User",
        location="26.9124, 75.7873",
        nearby_places={
            "police": {"name": "Police Station", "distance_m": 450, "address": "Main Road"},
            "hospital": {"name": "Hospital", "distance_m": 680, "address": "Civil Lines"}
        }
    )
    
    print(f"\nResult: {result}")
    return result


if __name__ == "__main__":
    test_email()
