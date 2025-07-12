from pydantic import BaseModel, Field, EmailStr
from typing import Dict
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


class UserBase(BaseModel):
    email: EmailStr
    phone: str
    is_creator: bool

class Creator(UserBase):
    is_creator: bool = True
    socials: Dict[str, str] 

class Business(UserBase):
    is_creator: bool = False
    category: str 
