from fastapi import APIRouter
from src.api.v1 import users, ai, emergency, live_tracking

api_router = APIRouter()

api_router.include_router(users.router, prefix="/api/v1/users")
api_router.include_router(ai.router, prefix="/api/v1/ai")
api_router.include_router(emergency.router, prefix="/api/v1/emergency")
api_router.include_router(live_tracking.router, prefix="/api/v1")  # ← NEW!