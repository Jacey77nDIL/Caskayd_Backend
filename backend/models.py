from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, BigInteger, Float, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional, List
from datetime import datetime
from database import Base

# Pydantic models (for API requests/responses)
class CreatorSignUp(BaseModel):
    category: str
    email: EmailStr
    password: str

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


class UserCreator(Base):
    __tablename__ = "users_creators"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversations = relationship("Conversation", foreign_keys="Conversation.creator_id", back_populates="creator")
    # 👇 Add this to connect to CreatorSocial
    socials = relationship("InstagramCreatorSocial", back_populates="user", cascade="all, delete")

class UserBusiness(Base):
    __tablename__ = "users_businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    business_name = Column(String, nullable=False)
    website_url = Column(String, nullable=True)
    socials = Column(JSON, nullable=True)  # Store as JSON
    business_bio = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversations = relationship("Conversation", foreign_keys="Conversation.business_id", back_populates="business")

class InstagramCreatorSocial(Base):
    """
    One row per user per platform (instagram). Holds the latest snapshot + tokens + timestamps.
    """
    __tablename__ = "instagram_creator_socials"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    platform = Column(String(32), nullable=False, default="instagram")  # 'instagram'
    facebook_page_id = Column(String(64))            # connected page id
    facebook_page_name = Column(String(255))         # convenience
    instagram_user_id = Column(String(64), index=True)
    instagram_username = Column(String(255))

    followers_count = Column(Integer)
    reach_7d = Column(Integer)
    engagement_rate = Column(Float)  # percentage, e.g. 3.25

    long_lived_token = Column(Text, nullable=True)
    token_last_updated_at = Column(DateTime(timezone=True))
    insights_last_updated_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship back to the UserCreator
    user = relationship("UserCreator", back_populates="socials")

    __table_args__ = (
        UniqueConstraint("user_id", "platform", name="uq_user_platform"),
        Index("ix_creator_socials_insights_updated", "insights_last_updated_at"),
        Index("ix_creator_socials_token_updated", "token_last_updated_at"),
        Index("ix_creator_socials_user_platform", "user_id", "platform"),
    )

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("users_creators.id"), nullable=False)
    business_id = Column(Integer, ForeignKey("users_businesses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    creator = relationship("UserCreator", foreign_keys=[creator_id], back_populates="conversations")
    business = relationship("UserBusiness", foreign_keys=[business_id], back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(String, nullable=False)  
    sender_id = Column(Integer, nullable=False)  
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

# Pydantic response models
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