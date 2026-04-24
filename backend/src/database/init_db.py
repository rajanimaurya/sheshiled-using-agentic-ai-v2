from .session import engine, Base
from src.core.config import settings
import asyncpg
from src.models.user import User 
from src.models.emergency import EmergencyContact
from src.models.ai_log import AIActivityLog

async def ensure_database():
    """Create database if not exists"""
    try:
        conn = await asyncpg.connect(
            user=settings.DB_USER,
            password=settings.DB_PASS,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            database='postgres'
        )
        
        # fetchval ✅ (fetch_val nahi)
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", 
            settings.DB_NAME
        )
        
        if not db_exists:
            print(f"Creating database: {settings.DB_NAME}")
            await conn.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
            print("Database created successfully!")
        else:
            print(f"Database {settings.DB_NAME} already exists")
            
        await conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

async def init_models():
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database Tables Created Successfully!")


async def init_db():
    """Main entry point for database initialization"""
    # Supabase par 'ensure_database' ki zarurat nahi hai, 
    # isliye seedha init_models call karenge.
    print("Starting Table Migration on Supabase...")
    await init_models()
    print("Migration Complete!")    