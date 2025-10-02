from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


class CreatorSignUp(BaseModel):
    category: str
    email: EmailStr
    password: str
    name:str
    bio:str


class BusinessSignUp(BaseModel):
    category: str
    email: EmailStr
    password: str
    business_name: str
    website_url: str
    socials: dict[str, str]
    business_bio: str

class Login(BaseModel):
    email: EmailStr
    password: str

class GoogleToken(BaseModel):
    token: str

class GoogleSignUp(BaseModel):
    category: str
    token: str
    business_name: Optional[str] = None

class MessageCreate(BaseModel):
    conversation_id: int
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_type: str
    sender_id: int
    content: str
    created_at: datetime
    is_read: bool
    
    class Config:
        from_attributes = True

class ConversationCreate(BaseModel):
    creator_email: str
    initial_message: str

class ConversationResponse(BaseModel):
    id: int
    creator_id: int
    business_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    creator_email: str
    business_name: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread_count: int = 0
    
    class Config:
        from_attributes = True

class ConversationDetail(BaseModel):
    id: int
    creator_id: int
    business_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    creator_email: str
    business_name: str
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class CreatorProfileSetup(BaseModel):
    name: str
    bio: Optional[str] = None
    location: Optional[str] = None
    followers_count: Optional[int] = None
    engagement_rate: Optional[str] = None
    profile_image: Optional[str] = None
    niche_ids: List[int] = []
