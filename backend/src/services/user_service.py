from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.schemas.user_schema import UserCreate, UserUpdate
from src.models.user import User
from src.models.emergency import EmergencyContact
from fastapi import HTTPException, status
from src.core.security import hash_password

class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, data: UserCreate):
        # 1. Validation: Check if exists
        query = select(User).where(
            or_(
                User.username == data.username.lower(),
                User.email == data.email.lower(),
                User.phone == data.phone
            )
        )
        result = await db.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.username == data.username.lower():
                raise HTTPException(status_code=400, detail="Username already taken")
            if existing_user.email == data.email.lower():
                raise HTTPException(status_code=400, detail="Email already exists")
            if existing_user.phone == data.phone:
                raise HTTPException(status_code=400, detail="Phone number already registered")

        # 2. Create User (Main Table)
        new_user = User(
            username=data.username.lower(),
            name=data.name,
            email=data.email.lower(),
            phone=data.phone,
            hashed_password=hash_password(data.password)
        )
        
        db.add(new_user)
        await db.flush()
        
        # 3. Create Emergency Contact (3NF Table)
        if any([data.emergency_name, data.emergency_phone, data.emergency_relation, data.emergency_email]):
            emergency_contact = EmergencyContact(
                user_id=new_user.id,
                name=data.emergency_name,
                phone=data.emergency_phone,
                relation=data.emergency_relation,
                email=data.emergency_email
            )
            db.add(emergency_contact)
        
        await db.commit()
        return await UserService.get_user(db, new_user.id)

    @staticmethod
    async def get_user_for_login(db: AsyncSession, login_id: str):
        """Flexible Login: Username, Email, ya Phone teeno check karega"""
        query = select(User).where(
            or_(
                User.username == login_id.lower(),
                User.email == login_id.lower(),
                User.phone == login_id
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user(db: AsyncSession, user_id: int):
        # selectinload se 3NF relationship data (EmergencyContact) load hoga
        result = await db.execute(
            select(User)
            .options(selectinload(User.emergency_contacts))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    @staticmethod
    async def get_users(db: AsyncSession):
        result = await db.execute(
            select(User).options(selectinload(User.emergency_contacts))
        )
        return result.scalars().all()

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, data: UserUpdate):
        # User load with relationship
        user = await UserService.get_user(db, user_id)
        update_data = data.model_dump(exclude_unset=True)
        
        # Separate User data and Emergency data
        emergency_fields = ['emergency_name', 'emergency_phone', 'emergency_relation', 'emergency_email']
        
        for key, value in update_data.items():
            if key in emergency_fields:
                if user.emergency_contacts:
                    attr_name = key.replace('emergency_', '')
                    setattr(user.emergency_contacts[0], attr_name, value)
                else:
                    new_contact = EmergencyContact(user_id=user.id)
                    setattr(new_contact, key.replace('emergency_', ''), value)
                    db.add(new_contact)
            elif hasattr(user, key):
                setattr(user, key, value)
        
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int):
        user = await UserService.get_user(db, user_id)
        await db.delete(user)
        await db.commit()
        return True

    # ─────────────────────────────────────────────
    #  SECRET CODE — Save & Verify
    # ─────────────────────────────────────────────

    @staticmethod
    async def set_secret_code(db: AsyncSession, user_id: int, secret_code: str) -> bool:
        """User ka distress word save karo (lowercase mein)."""
        user = await UserService.get_user(db, user_id)
        user.secret_code = secret_code.strip().lower()
        await db.commit()
        return True

    @staticmethod
    async def verify_secret_code(user, message: str) -> bool:
        """
        Check karo ki user ka message uska secret code hai ya nahi.
        Returns True → SOS trigger karni chahiye.
        """
        code = getattr(user, "secret_code", None)
        if not code:
            return False
        return message.strip().lower() == code.strip().lower()