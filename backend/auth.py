from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Creator, Business
from passlib.context import CryptContext
from jose import jwt
import os
from google.oauth2 import id_token
from google.auth.transport import requests

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hash_password(password):
    return pwd_context.hash(password)

async def is_email_used(email: str, db: AsyncSession):
    creator_query = await db.execute(select(Creator).where(Creator.email == email))
    business_query = await db.execute(select(Business).where(Business.email == email))
    return creator_query.scalar() or business_query.scalar()

async def signup_creator(data, db: AsyncSession):
    if await is_email_used(data.email, db):
        return None
    hashed = hash_password(data.password)
    user = Creator(email=data.email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    return create_access_token({"sub": data.email, "role": "creator"})

async def signup_business(data, db: AsyncSession):
    if await is_email_used(data.email, db):
        return None
    hashed = hash_password(data.password)
    user = Business(email=data.email, business_name=data.business_name, hashed_password=hashed)
    db.add(user)
    await db.commit()
    return create_access_token({"sub": data.email, "role": "business"})

async def login(data, db: AsyncSession):
    for model, role in [(Creator, "creator"), (Business, "business")]:
        result = await db.execute(select(model).where(model.email == data.email))
        user = result.scalar()
        if user and verify_password(data.password, user.hashed_password):
            return create_access_token({"sub": user.email, "role": role})
    return None

async def signup_with_google(data, db: AsyncSession):
    # Verify the Google token and get the email
    try:
        idinfo = id_token.verify_oauth2_token(data.token, requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo["email"]
    except Exception:
        return None

    # If user already exists, just issue token with correct role
    creator = await db.execute(select(Creator).where(Creator.email == email))
    business = await db.execute(select(Business).where(Business.email == email))
    existing_creator = creator.scalar()
    existing_business = business.scalar()

    if existing_creator:
        return create_access_token({"sub": email, "role": "creator"})
    if existing_business:
        return create_access_token({"sub": email, "role": "business"})

    # New user - create based on category
    hashed = hash_password("google_" + email)  # Dummy password for Google signup

    if data.category.lower() == "business":
        if not data.business_name:
            return None
        user = Business(email=email, business_name=data.business_name, hashed_password=hashed)
        db.add(user)
        role = "business"
    else:
        user = Creator(email=email, hashed_password=hashed)
        db.add(user)
        role = "creator"

    await db.commit()
    return create_access_token({"sub": email, "role": role})


async def login_with_google(token: str, db: AsyncSession):
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo["email"]
    except Exception:
        return None

    creator = await db.execute(select(Creator).where(Creator.email == email))
    business = await db.execute(select(Business).where(Business.email == email))
    existing_creator = creator.scalar()
    existing_business = business.scalar()

    if existing_creator:
        return create_access_token({"sub": email, "role": "creator"})
    if existing_business:
        return create_access_token({"sub": email, "role": "business"})

    # User not found, must signup first
    return None
