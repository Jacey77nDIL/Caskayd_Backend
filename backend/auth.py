from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import UserCreator, UserBusiness  # SQLAlchemy models
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
    creator_query = await db.execute(select(UserCreator).where(UserCreator.email == email))
    business_query = await db.execute(select(UserBusiness).where(UserBusiness.email == email))
    return creator_query.scalar_one_or_none() or business_query.scalar_one_or_none()


async def signup_creator(data, db: AsyncSession):
    if await is_email_used(data.email, db):
        return None

    hashed = hash_password(data.password)
    user = UserCreator(
        category=data.category,
        email=data.email,
        password_hash=hashed
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return create_access_token({"sub": data.email, "role": "creator"})


async def signup_business(data, db: AsyncSession):
    if await is_email_used(data.email, db):
        return None

    hashed = hash_password(data.password)
    user = UserBusiness(
        category=data.category,
        email=data.email,
        password_hash=hashed,
        business_name=data.business_name,
        website_url=data.website_url,
        socials=data.socials,
        business_bio=data.business_bio,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return create_access_token({"sub": data.email, "role": "business"})


async def login(data, db: AsyncSession):
    for model, role in [(UserCreator, "creator"), (UserBusiness, "business")]:
        result = await db.execute(select(model).where(model.email == data.email))
        user = result.scalar_one_or_none()
        if user and verify_password(data.password, user.password_hash):
            return create_access_token({"sub": user.email, "role": role})
    return None


async def signup_with_google(data, db: AsyncSession):
    try:
        idinfo = id_token.verify_oauth2_token(data.token, requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo["email"]
    except Exception:
        return None

    creator = await db.execute(select(UserCreator).where(UserCreator.email == email))
    business = await db.execute(select(UserBusiness).where(UserBusiness.email == email))
    existing_creator = creator.scalar_one_or_none()
    existing_business = business.scalar_one_or_none()

    if existing_creator:
        return create_access_token({"sub": email, "role": "creator"})
    if existing_business:
        return create_access_token({"sub": email, "role": "business"})

    # New user - create based on category
    hashed = hash_password("google_" + email)  # dummy password

    if data.category.lower() == "business":
        if not data.business_name:
            return None
        user = UserBusiness(
            category=data.category,
            email=email,
            password_hash=hashed,
            business_name=data.business_name,
        )
        role = "business"
    else:
        user = UserCreator(
            category=data.category,
            email=email,
            password_hash=hashed,
        )
        role = "creator"

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return create_access_token({"sub": email, "role": role})


async def login_with_google(token: str, db: AsyncSession):
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo["email"]
    except Exception:
        return None

    creator = await db.execute(select(UserCreator).where(UserCreator.email == email))
    business = await db.execute(select(UserBusiness).where(UserBusiness.email == email))
    existing_creator = creator.scalar_one_or_none()
    existing_business = business.scalar_one_or_none()

    if existing_creator:
        return create_access_token({"sub": email, "role": "creator"})
    if existing_business:
        return create_access_token({"sub": email, "role": "business"})

    return None
