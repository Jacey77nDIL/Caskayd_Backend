from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import UserCreator, UserBusiness  # SQLAlchemy models
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
FB_APP_ID = os.getenv("FB_APP_ID", "")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI")

JWT_ALGORITHM = os.getenv("ALGORITHM")
JWT_SECRET = os.getenv("SECRET_KEY")  # used if algorithm is HS256

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
        password_hash=hashed,
        bio=data.bio,
        name=data.name
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

def decode_jwt_from_header(authorization_header: str) -> dict:
    """
    Expects 'Authorization: Bearer <jwt>'.
    Returns the decoded JWT payload.
    """
    if not authorization_header or not authorization_header.lower().startswith("bearer "):
        raise ValueError("Missing or invalid Authorization header.")

    token = authorization_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid JWT: {e}")
    
# --- In auth.py ---

async def decode_user_id_from_jwt(payload: dict, db: AsyncSession): # <-- THE FIX IS HERE
    """
    Gets the user model instance (Creator or Business) from a
    decoded JWT payload.
    """
    email = payload.get("sub")
    role = payload.get("role")

    if not email or not role:
        raise ValueError("JWT missing 'sub' or 'role' claim.")

    if role == "creator":
        model = UserCreator
    elif role == "business":
        model = UserBusiness
    else:
        raise ValueError(f"Invalid 'role' in JWT: {role}")

    result = await db.execute(select(model).where(model.email == email))
    user = result.scalar()

    if not user:
        raise ValueError("User in JWT not found in database.")

    return user, role