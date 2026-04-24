from fastapi import APIRouter, Depends, HTTPException, Path, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel
from src.database.session import get_db
from src.schemas.emergency import EmergencyContactCreate, EmergencyContactResponse
from src.api.dependencies.auth import get_current_user
from src.services.emergency_service import EmergencyService
from src.services.sos_nearby_integration import trigger_sos_emergency, SheShieldSOSNearby

router = APIRouter(tags=["emergency_contact"])

# ========== PYDANTIC MODELS ==========
class SOSRequest(BaseModel):
    """SOS request with GPS location"""
    latitude: float
    longitude: float
    radius: int = 2000  # Default 2km radius

# ========== EMERGENCY CONTACT ENDPOINTS ==========

@router.post("/", response_model=EmergencyContactResponse)
async def add_emergency_contact(
    contact_in: EmergencyContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Naya emergency contact add karne ke liye"""
    return await EmergencyService.add_contact(db, current_user.id, contact_in)

@router.get("/", response_model=List[EmergencyContactResponse])
async def get_my_emergency_contacts(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """User ke saare contacts dekhne ke liye"""
    return await EmergencyService.get_user_contacts(db, current_user.id)

@router.put("/{contact_id}", response_model=EmergencyContactResponse)
async def update_emergency_contact(
    contact_in: EmergencyContactCreate,
    contact_id: int = Path(..., gt=0, description="The ID of the contact to update"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Contact ki details update karne ke liye"""
    updated = await EmergencyService.update_contact(db, contact_id, current_user.id, contact_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found or unauthorized")
    return updated

@router.delete("/{contact_id}")
async def delete_emergency_contact(
    contact_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Contact delete karne ke liye"""
    success = await EmergencyService.delete_contact(db, contact_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found or unauthorized")
    return {"message": "Emergency contact deleted successfully"}

# ========== SOS ENDPOINTS (NEW) ==========

@router.post("/sos/trigger")
async def trigger_sos(
    data: SOSRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    🚨 SOS EMERGENCY TRIGGER
    
    Complete SOS flow:
    1. Captures live GPS location
    2. Finds nearest safe places (1-2km)
    3. Sends HTML email to all emergency contacts with routes
    4. Returns confirmation
    
    Request:
    {
        "latitude": 26.9124,
        "longitude": 75.7873,
        "radius": 2000
    }
    """
    
    # Get user's emergency contacts
    contacts = await EmergencyService.get_user_contacts(db, current_user.id)
    
    if not contacts:
        raise HTTPException(
            status_code=400,
            detail="No emergency contacts found. Please add at least one."
        )
    
    # Extract emails
    recipient_emails = [c.email for c in contacts if c.email]
    
    if not recipient_emails:
        raise HTTPException(
            status_code=400,
            detail="No email addresses in emergency contacts"
        )
    
    # Trigger SOS in background
    background_tasks.add_task(
        trigger_sos_emergency,
        recipient_emails=recipient_emails,
        user_name=current_user.name or "SheShield User",
        latitude=data.latitude,
        longitude=data.longitude
    )
    
    return {
        "status": "SOS_TRIGGERED",
        "message": f"Emergency alerts being sent to {len(recipient_emails)} contact(s)",
        "location": {
            "latitude": data.latitude,
            "longitude": data.longitude,
            "maps_link": f"https://maps.google.com?q={data.latitude},{data.longitude}"
        },
        "contacts_notified": len(recipient_emails),
        "radius_meters": data.radius
    }

@router.post("/sos/preview")
async def preview_sos(
    data: SOSRequest,
    current_user = Depends(get_current_user)
):
    """
    Preview what the SOS email will look like before triggering.
    
    Useful for testing and understanding the alert format.
    
    Returns: Nearby places + HTML preview
    """
    
    # Find nearby places
    nearby_places = SheShieldSOSNearby.find_nearby_places(
        data.latitude, 
        data.longitude,
        data.radius or 2000
    )
    
    # Generate HTML preview
    subject, html_body = SheShieldSOSNearby.generate_html_email(
        "preview@example.com",
        current_user.name or "SheShield User",
        data.latitude,
        data.longitude,
        nearby_places,
        "Preview Time"
    )
    
    return {
        "status": "PREVIEW",
        "location": {
            "latitude": data.latitude,
            "longitude": data.longitude,
            "maps_link": f"https://maps.google.com?q={data.latitude},{data.longitude}"
        },
        "nearby_places": {
            key: place.to_dict() if place else None 
            for key, place in nearby_places.items()
        },
        "email_preview": {
            "subject": subject,
            "html_body": html_body
        }
    }