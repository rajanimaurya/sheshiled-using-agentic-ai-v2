# Database session configuration
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.core.config import settings
import asyncio

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# DB connection check
async def test_db_connection():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda conn: None) 
        print(" Database connected successfully")
    except Exception as e:
        print(f" Database connection failed: {e}")

# asyncio.run(test_db_connection()) 

async def get_db():
    async with SessionLocal() as db:
        yield db
