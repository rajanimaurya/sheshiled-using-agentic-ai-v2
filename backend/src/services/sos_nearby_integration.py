import os
import asyncio
import smtplib
import math
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from typing import Optional, List, Dict
import requests

load_dotenv()


class NearbyPlace:
    """Data class for nearby places"""
    def __init__(self, name: str, place_type: str, distance: int, address: str, lat: float, lng: float):
        self.name = name
        self.place_type = place_type
        self.distance = distance
        self.address = address
        self.lat = lat
        self.lng = lng

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.place_type,
            "distance": self.distance,
            "address": self.address,
            "lat": self.lat,
            "lng": self.lng
        }


class SheShieldSOSNearby:
    """Integrated SOS + Nearby Places Service"""

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
        """Calculate distance in metres between two GPS coordinates"""
        R = 6_371_000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    @staticmethod
    def find_nearby_places(latitude: float, longitude: float, radius: int = 2000) -> Dict[str, Optional[NearbyPlace]]:
        """
        Find nearby places using Google Places Nearby Search API.
        Returns a dict with keys: hospital, police, mall, restaurant
        """
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            return {
                "hospital": None, "police": None, "mall": None, "restaurant": None,
                "error": "Google Maps API key missing"
            }

        places_api_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

        categories = {
            "hospital": {"type": "hospital", "label": "Hospital"},
            "police": {"type": "police", "label": "Police Station"},
            "mall": {"type": "shopping_mall", "label": "Shopping Mall"},
            "restaurant": {"type": "restaurant", "label": "Restaurant"},
        }

        results = {"hospital": None, "police": None, "mall": None, "restaurant": None}

        for key, meta in categories.items():
            try:
                params = {
                    "location": f"{latitude},{longitude}",
                    "radius": radius,
                    "type": meta["type"],
                    "key": api_key,
                }
                response = requests.get(places_api_url, params=params, timeout=10)
                data = response.json()

                if data.get("status") != "OK":
                    continue

                places_raw = data.get("results", [])
                if not places_raw:
                    continue

                # Find nearest place
                nearest = None
                min_distance = float('inf')

                for place in places_raw:
                    loc = place.get("geometry", {}).get("location", {})
                    p_lat = loc.get("lat")
                    p_lng = loc.get("lng")

                    if not p_lat or not p_lng:
                        continue

                    dist = SheShieldSOSNearby.haversine_distance(latitude, longitude, p_lat, p_lng)

                    if dist < min_distance:
                        min_distance = dist
                        nearest = NearbyPlace(
                            name=place.get("name", meta["label"]),
                            place_type=meta["label"],
                            distance=dist,
                            address=place.get("vicinity", "Address unavailable"),
                            lat=p_lat,
                            lng=p_lng
                        )

                results[key] = nearest

            except Exception as e:
                print(f"Error fetching {key}: {e}")
                continue

        return results

    @staticmethod
    def generate_html_email(
        recipient_email: str,
        user_name: str,
        latitude: float,
        longitude: float,
        nearby_places: Dict[str, Optional[NearbyPlace]],
        timestamp: str
    ) -> tuple:
        """Generate HTML email with location and nearby places"""

        maps_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        maps_embed = f"https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d3600!2d{longitude}!3d{latitude}!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zM!5e0!3m2!1sen!2sin!4v1234567890"

        # Build nearby places HTML
        nearby_html = ""
        for key, place in nearby_places.items():
            if place:
                icon_map = {
                    "hospital": "🏥",
                    "police": "🚔",
                    "mall": "🏬",
                    "restaurant": "🍽️"
                }
                icon = icon_map.get(key, "📍")
                place_maps_link = f"https://www.google.com/maps?q={place.lat},{place.lng}"

                nearby_html += f"""
                <tr style="border-bottom: 1px solid #e0e0e0;">
                    <td style="padding: 12px; text-align: center;">{icon}</td>
                    <td style="padding: 12px;">
                        <strong>{place.name}</strong><br>
                        <small style="color: #666;">{place.distance}m away</small><br>
                        <small style="color: #888;">{place.address}</small>
                    </td>
                    <td style="padding: 12px;">
                        <a href="{place_maps_link}" style="color: #007AFF; text-decoration: none; font-weight: 500;">View →</a>
                    </td>
                </tr>
                """

        # Build HTML email
        html_body = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #f9f9f9; border-radius: 10px; overflow: hidden; }}
                    .header {{ background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; background: white; }}
                    .location-box {{ background: #fff3cd; border-left: 4px solid #ff6b6b; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .location-box h3 {{ margin: 0 0 10px 0; color: #d32f2f; }}
                    .location-box p {{ margin: 5px 0; font-size: 14px; }}
                    .nearby-places {{ margin: 30px 0; }}
                    .nearby-places h3 {{ color: #333; margin-bottom: 15px; }}
                    .nearby-table {{ width: 100%; border-collapse: collapse; background: #f5f5f5; border-radius: 5px; overflow: hidden; }}
                    .nearby-table td {{ padding: 12px; }}
                    .button {{ display: inline-block; padding: 12px 24px; background: #007AFF; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: 500; }}
                    .footer {{ background: #f5f5f5; padding: 20px; text-align: center; color: #666; font-size: 12px; }}
                    .warning {{ color: #d32f2f; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚨 SOS ALERT - IMMEDIATE ASSISTANCE NEEDED</h1>
                        <p style="margin: 10px 0 0 0; font-size: 14px;">Time: {timestamp}</p>
                    </div>

                    <div class="content">
                        <p><strong>Dear Safety Contact,</strong></p>

                        <p>This is an <span class="warning">URGENT SOS alert</span> from the <strong>SheShield Women's Safety App</strong>.</p>

                        <p><strong>{user_name}</strong> has triggered the emergency SOS button and needs <strong>immediate help</strong>.</p>

                        <!-- Location Information -->
                        <div class="location-box">
                            <h3>📍 Current Location</h3>
                            <p><strong>Coordinates:</strong> {latitude:.6f}, {longitude:.6f}</p>
                            <p><strong>Accuracy:</strong> High precision GPS</p>
                            <a href="{maps_link}" class="button" style="display: inline-block;">🗺️ View on Google Maps</a>
                        </div>

                        <!-- Nearby Safety Places -->
                        <div class="nearby-places">
                            <h3>🏛️ Nearby Safety Places</h3>
                            <p style="color: #666; margin-bottom: 15px;">These locations are within 2km radius and can provide immediate assistance:</p>
                            <table class="nearby-table">
                                {nearby_html if nearby_html else '<tr><td colspan="3" style="padding: 20px; text-align: center; color: #999;">No nearby places found in 2km radius</td></tr>'}
                            </table>
                        </div>

                        <!-- Instructions -->
                        <div style="background: #f0f7ff; border-left: 4px solid #007AFF; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h4 style="margin-top: 0; color: #007AFF;">⚡ What to do immediately:</h4>
                            <ul style="margin: 10px 0; padding-left: 20px;">
                                <li>Check the location on Google Maps</li>
                                <li>Call the nearest emergency service (Police, Hospital, or Nearby contacts)</li>
                                <li>Share the coordinates with local authorities if needed</li>
                                <li>Reach out to nearby places listed above</li>
                            </ul>
                        </div>

                        <p style="color: #999; font-size: 12px; margin-top: 30px;">
                            <strong>⚠️ Privacy Notice:</strong> This email contains sensitive location data. Please keep it confidential and secure. Delete after use if appropriate.
                        </p>
                    </div>

                    <div class="footer">
                        <p style="margin: 0;">🛡️ SheShield Women's Safety System</p>
                        <p style="margin: 5px 0;">Making India safer for women, one alert at a time.</p>
                        <p style="margin: 5px 0; color: #999;">If you received this email by mistake, please disregard it immediately.</p>
                    </div>
                </div>
            </body>
        </html>
        """

        subject = f"🚨 SOS ALERT: {user_name} needs immediate help - Location Shared"
        return subject, html_body

    @staticmethod
    async def send_sos_with_nearby_email(
        recipient_email: str,
        user_name: str,
        latitude: float,
        longitude: float,
        timestamp: str = None
    ) -> tuple[bool, str]:
        """
        Send SOS email with nearby places information.
        Returns: (success: bool, message: str)
        """
        sender_email = os.getenv("EMAIL_USER")
        sender_password = os.getenv("EMAIL_PASS")

        if not sender_email or not sender_password:
            return False, "Email service not configured in .env"

        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

        # Fetch nearby places
        nearby_places = SheShieldSOSNearby.find_nearby_places(latitude, longitude)

        # Generate HTML email
        subject, html_body = SheShieldSOSNearby.generate_html_email(
            recipient_email, user_name, latitude, longitude, nearby_places, timestamp
        )

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = recipient_email

            # Attach HTML
            msg.attach(MIMEText(html_body, "html"))

            # Send email
            with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
                smtp.starttls()
                smtp.login(sender_email, sender_password)
                smtp.send_message(msg)

            return True, f"SOS email with nearby places sent to {recipient_email}"

        except Exception as e:
            return False, f"Error sending email: {str(e)}"

    @staticmethod
    def get_maps_embed_link(latitude: float, longitude: float, nearby_places: Dict = None) -> Dict:
        """
        Generate Google Maps links and embed code for the response
        """
        view_link = f"https://www.google.com/maps?q={latitude},{longitude}"
        embed_link = f"https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d3600!2d{longitude}!3d{latitude}!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zM!5e0!3m2!1sen!2sin!4v1234567890"

        places_markers = []
        if nearby_places:
            for key, place in nearby_places.items():
                if place:
                    places_markers.append(place.to_dict())

        return {
            "view_link": view_link,
            "embed_link": embed_link,
            "places_markers": places_markers
        }


async def trigger_sos_emergency(
    recipient_emails: List[str],
    user_name: str,
    latitude: float,
    longitude: float,
    timestamp: str = None
) -> Dict:
    """
    Main function to trigger SOS with nearby places.
    Sends emails to all recipients and returns map links.
    """
    if not timestamp:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    # Get nearby places
    nearby_places = SheShieldSOSNearby.find_nearby_places(latitude, longitude)

    # Send emails to all recipients
    email_results = []
    for email in recipient_emails:
        success, message = await SheShieldSOSNearby.send_sos_with_nearby_email(
            email, user_name, latitude, longitude, timestamp
        )
        email_results.append({"email": email, "success": success, "message": message})

    # Get map links
    map_links = SheShieldSOSNearby.get_maps_embed_link(latitude, longitude, nearby_places)

    return {
        "sos_triggered": True,
        "timestamp": timestamp,
        "location": {"latitude": latitude, "longitude": longitude},
        "emails_sent": email_results,
        "nearby_places": {k: v.to_dict() if v else None for k, v in nearby_places.items()},
        "map_links": map_links
    }
