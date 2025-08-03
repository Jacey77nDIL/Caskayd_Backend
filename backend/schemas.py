from pydantic import BaseModel, EmailStr
from typing import Optional

class CreatorSignUp(BaseModel):
    category: str
    email: EmailStr
    password: str

class BusinessSignUp(BaseModel):
    category: str
    email: EmailStr
    password: str
    business_name: str

class Login(BaseModel):
    email: EmailStr
    password: str

class GoogleToken(BaseModel):
    token: str

class GoogleSignUp(BaseModel):
    category: str
    token: str
    business_name: Optional[str] = None