from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.database.init_db import ensure_database, init_models
from src.api.routers import api_router
import uvicorn
import os

app = FastAPI(title="Sheshield App")

# Railway pe CORS - sab origins allow (ya specific domain set karo env me)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    await ensure_database()
    await init_models()
    print("Database connected !")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("src.main:app", host="0.0.0.0", port=port, reload=False)
