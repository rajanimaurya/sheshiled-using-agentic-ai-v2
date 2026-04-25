from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.database.session import get_db
from src.schemas.user_schema import UserCreate, UserUpdate, UserOut, Token, LoginRequest, SecretCodeRequest, SecretCodeOut
from src.services.user_service import UserService
from src.api.dependencies.auth import get_current_user, get_current_admin
from src.models.user import User, UserRole
from src.core.security import verify_password, create_access_token

router = APIRouter(tags=["Users"])

# 1. LOGIN ENDPOINT
@router.post("/login", response_model=Token)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    user = await UserService.get_user_for_login(db, data.login_id)

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Login ID or Password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer"}


# 2. CREATE USER (Public Registration)
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db)):
    return await UserService.create_user(db, data)


# ✅ /me aur /me/secret-code — /{user_id} se PEHLE hone chahiye
# 3. GET MY PROFILE
@router.get("/me", response_model=UserOut)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


# 4. GET SECRET CODE
@router.get("/me/secret-code", response_model=SecretCodeOut)
async def get_secret_code(
    current_user: User = Depends(get_current_user),
):
    """User apna current secret code dekhe."""
    code = getattr(current_user, "secret_code", None)
    if not code:
        return SecretCodeOut(secret_code=None, message="not secert code added.")
    return SecretCodeOut(secret_code=code, message="this is yout current secret code.")


# 5. SET SECRET CODE
@router.post("/me/secret-code")
async def set_secret_code(
    data: SecretCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    User apna secret distress word save kare.
    Yeh word chat mein bolne par SOS silently trigger hoga.
    """
    await UserService.set_secret_code(db, current_user.id, data.secret_code)
    return {
        "message": "Secret code save✅",
        "hint":    "when you say , SOS automatically trigger .",
    }


# 6. GET ALL USERS (Admin only)
@router.get("/", response_model=List[UserOut])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return await UserService.get_users(db)


# ✅ /{user_id} routes — sabse BAAD mein
# 7. GET SINGLE USER
@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view this profile")

    return await UserService.get_user(db, user_id)


# 8. UPDATE USER
@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")

    return await UserService.update_user(db, user_id, data)


# 9. DELETE USER
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this profile")

    await UserService.delete_user(db, user_id)
    return None