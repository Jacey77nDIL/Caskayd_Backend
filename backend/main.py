from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
import schemas, auth
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

@app.post("/signup/creator")
async def signup_creator(data: schemas.CreatorSignUp, db: AsyncSession = Depends(get_db)):
    token = await auth.signup_creator(data, db)
    if not token:
        raise HTTPException(status_code=400, detail="Email already exists")
    return {"access_token": token}

@app.post("/signup/business")
async def signup_business(data: schemas.BusinessSignUp, db: AsyncSession = Depends(get_db)):
    token = await auth.signup_business(data, db)
    if not token:
        raise HTTPException(status_code=400, detail="Email already exists")
    return {"access_token": token}

@app.post("/login")
async def login(data: schemas.Login, db: AsyncSession = Depends(get_db)):
    token = await auth.login(data, db)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token}

@app.post("/signup/google")
async def signup_google(data: schemas.GoogleSignUp, db: AsyncSession = Depends(get_db)):
    token = await auth.signup_with_google(data, db)
    if not token:
        raise HTTPException(status_code=400, detail="Google signup failed")
    return {"access_token": token}

@app.post("/login/google")
async def login_google(data: schemas.GoogleToken, db: AsyncSession = Depends(get_db)):
    token = await auth.login_with_google(data.token, db)
    if not token:
        raise HTTPException(status_code=401, detail="Google login failed")
    return {"access_token": token}

@app.get("/get_current_user")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        return {"email": email, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")