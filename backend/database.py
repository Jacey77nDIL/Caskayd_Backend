from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os


DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    # This will fail the application with a clear error if the variable isn't set
    raise RuntimeError(
        "FATAL: The DATABASE_URL environment variable is missing. "
        "Please ensure it is set on the Render dashboard."
    )

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with SessionLocal() as session:
        yield session
