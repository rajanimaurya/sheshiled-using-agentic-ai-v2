from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.emergency import EmergencyContact
from src.schemas.emergency import EmergencyContactCreate
from fastapi import HTTPException

class EmergencyService:
    @staticmethod
    async def add_contact(db: AsyncSession, user_id: int, contact_in: EmergencyContactCreate):
        # 1. Check if number already exists for this user
        query = select(EmergencyContact).where(
            EmergencyContact.user_id == user_id,
            EmergencyContact.phone == contact_in.phone
        )
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="This phone number is already in your emergency contacts")

        try:
            new_contact = EmergencyContact(user_id=user_id, **contact_in.dict())
            db.add(new_contact)
            await db.commit()
            await db.refresh(new_contact)
            return new_contact
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

    @staticmethod
    async def get_user_contacts(db: AsyncSession, user_id: int):
        query = select(EmergencyContact).where(EmergencyContact.user_id == user_id)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_contact(db: AsyncSession, contact_id: int, user_id: int, contact_in: EmergencyContactCreate):
        query = select(EmergencyContact).where(
            EmergencyContact.id == contact_id, 
            EmergencyContact.user_id == user_id
        )
        result = await db.execute(query)
        db_contact = result.scalar_one_or_none()
        
        if not db_contact:
            return None
            
        try:
            update_data = contact_in.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_contact, key, value)
            
            await db.commit()
            await db.refresh(db_contact)
            return db_contact
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update contact")

    @staticmethod
    async def delete_contact(db: AsyncSession, contact_id: int, user_id: int):
        query = select(EmergencyContact).where(
            EmergencyContact.id == contact_id,
            EmergencyContact.user_id == user_id
        )
        result = await db.execute(query)
        db_contact = result.scalar_one_or_none()
        
        if not db_contact:
            return False
            
        try:
            await db.delete(db_contact)
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete contact")