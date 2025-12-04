import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Get the URL from Render
database_url = os.getenv("DATABASE_URL")

# 2. THE FIX: Force the URL to use the async driver
# If the URL starts with 'postgres://' or 'postgresql://', switch it to 'postgresql+asyncpg://'
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# 3. Now create the engine with the FIXED url
engine = create_async_engine(database_url, echo=True)

# ... rest of your code (SessionLocal, Base, etc.) ...
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session
