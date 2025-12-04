from pydantic import BaseModel, EmailStr
from sqlalchemy import Column, Integer, String, Table, Text, DateTime, ForeignKey, Boolean, JSON, BigInteger, Float, UniqueConstraint, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional, List
from datetime import datetime
from database import Base
import enum

creator_niches = Table('creator_niches', Base.metadata,
    Column('creator_id', Integer, ForeignKey('users_creators.id')),
    Column('niche_id', Integer, ForeignKey('niches.id'))
)

business_industries = Table('business_industries', Base.metadata,
    Column('business_id', Integer, ForeignKey('users_businesses.id')),
    Column('industry_id', Integer, ForeignKey('industries.id'))
)

industry_niches = Table('industry_niches', Base.metadata,
    Column('industry_id', Integer, ForeignKey('industries.id')),
    Column('niche_id', Integer, ForeignKey('niches.id'))
)

class UserCreator(Base):
    __tablename__ = "users_creators"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    bio = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    location = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    followers_count = Column(Integer, nullable=True)  # Added this field
    engagement_rate = Column(Float, nullable=True)  # Added for storing engagement rate as float
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversations = relationship("Conversation", foreign_keys="Conversation.creator_id", back_populates="creator")
    socials = relationship("InstagramCreatorSocial", back_populates="user", cascade="all, delete")
    niches = relationship("Niche", secondary=creator_niches, back_populates="creators")

class UserBusiness(Base):
    __tablename__ = "users_businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    business_name = Column(String, nullable=False)
    website_url = Column(String, nullable=True)
    socials = Column(JSON, nullable=True)
    business_bio = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    conversations = relationship("Conversation", foreign_keys="Conversation.business_id", back_populates="business")
    industries = relationship("Industry", secondary=business_industries, back_populates="businesses")

class InstagramCreatorSocial(Base):
    """
    One row per user per platform (instagram). Holds the latest snapshot + tokens + timestamps.
    """
    __tablename__ = "instagram_creator_socials"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users_creators.id", ondelete="CASCADE"), nullable=False)

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
    content = Column(Text, nullable=True) 
    file_url = Column(String(1024), nullable=True)
    file_type = Column(String(100), nullable=True)
    

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)
    
    conversation = relationship("Conversation", back_populates="messages")

class Niche(Base):
    __tablename__ = "niches"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    # Relationships
    creators = relationship("UserCreator", secondary=creator_niches, back_populates="niches")
    industries = relationship("Industry", secondary=industry_niches, back_populates="niches")

class Industry(Base):
    __tablename__ = "industries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    # Relationships
    businesses = relationship("UserBusiness", secondary=business_industries, back_populates="industries")
    niches = relationship("Niche", secondary=industry_niches, back_populates="industries")

class BusinessCreatorInteraction(Base):
    __tablename__ = "business_creator_interactions"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('users_businesses.id'), nullable=False)
    creator_id = Column(Integer, ForeignKey('users_creators.id'), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())
    interaction_type = Column(String, default='viewed')  # viewed, contacted, hired, etc.

class RecommendationCache(Base):
    __tablename__ = "recommendation_cache"
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('users_businesses.id'), nullable=False)
    cache_key = Column(String, nullable=False)  # hash of filters + search
    creator_ids = Column(Text, nullable=False)  # JSON string of creator IDs in order
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())

class TransactionStatus(enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    abandoned = "abandoned"

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String, unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="NGN")
    email = Column(String, nullable=False)
    status = Column(SQLEnum(TransactionStatus), default=TransactionStatus.pending)
    
    # User information
    user_id = Column(Integer, nullable=True)  # Payer (Business)
    user_type = Column(String, nullable=True)  # 'creator' or 'business'
    recipient_id = Column(Integer, nullable=True) # Payee (Creator)
    
    # Transaction details
    authorization_url = Column(Text, nullable=True)
    access_code = Column(String, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    purpose = Column(String, nullable=True)  # e.g., 'subscription', 'campaign_payment'
    transaction_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CreatorCampaignStatus(str, enum.Enum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REMOVED = "removed"

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("users_businesses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # --- 3. Change brief from Text to a file URL ---
    brief = Column(Text, nullable=True) 
    brief_file_url = Column(String(1024), nullable=True)
    # -----------------------------------------------

    budget = Column(Float, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    business = relationship("UserBusiness", backref="campaigns")
    campaign_creators = relationship("CampaignCreator", back_populates="campaign", cascade="all, delete-orphan")

class CampaignCreator(Base):
    __tablename__ = "campaign_creators"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users_creators.id"), nullable=False)
    status = Column(SQLEnum(CreatorCampaignStatus), default=CreatorCampaignStatus.INVITED, nullable=False)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)  # Business notes about this creator for the campaign
    
    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_creators")
    creator = relationship("UserCreator", backref="campaign_participations")

# --- Add this class to models.py ---

class TikTokCreatorSocial(Base):
    """
    Stores TikTok OAuth tokens and basic insights for a creator.
    """
    __tablename__ = "tiktok_creator_socials"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users_creators.id", ondelete="CASCADE"), nullable=False)
    
    platform = Column(String(32), nullable=False, default="tiktok")
    open_id = Column(String(128), index=True, nullable=False) # TikTok's user ID
    union_id = Column(String(128), index=True)
    
    tiktok_username = Column(String(255))
    display_name = Column(String(255))
    profile_image_url = Column(Text)

    followers_count = Column(BigInteger)
    likes_count = Column(BigInteger)
    video_count = Column(Integer)
    
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True))
    refresh_token_expires_at = Column(DateTime(timezone=True))
    
    token_last_updated_at = Column(DateTime(timezone=True))
    insights_last_updated_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship back to the UserCreator
    user = relationship("UserCreator", backref="tiktok_socials")

    __table_args__ = (
        UniqueConstraint("user_id", "platform", name="uq_user_platform_tiktok"),
        Index("ix_tiktok_socials_open_id", "open_id"),
    )

class InstagramAnalyticsHistory(Base):
    """
    Stores historical Instagram analytics snapshots for tracking trends.
    """
    __tablename__ = "instagram_analytics_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users_creators.id", ondelete="CASCADE"), nullable=False)
    instagram_user_id = Column(String(64), nullable=False)
    
    # Analytics snapshot
    followers_count = Column(Integer)
    reach_7d = Column(Integer)
    engagement_rate = Column(Float)
    impressions_7d = Column(Integer)
    profile_views_7d = Column(Integer)
    website_clicks_7d = Column(Integer)
    saves_7d = Column(Integer)
    shares_7d = Column(Integer)
    
    # Metadata
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship back to the UserCreator
    user = relationship("UserCreator", backref="instagram_analytics_history")

    __table_args__ = (
        Index("ix_analytics_history_user_date", "user_id", "recorded_at"),
        Index("ix_analytics_history_user_ig_id", "user_id", "instagram_user_id"),
    )

class BankAccount(Base):
    """
    Stores creator's bank account details for payouts.
    """
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_creators.id"), nullable=False, unique=True)
    account_number = Column(String, nullable=False)
    account_name = Column(String, nullable=False)
    bank_code = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    recipient_code = Column(String, nullable=True)  # Paystack recipient code (RCP_...)
    currency = Column(String, default="NGN")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("UserCreator", backref="bank_account")

class PayoutStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REVERSED = "reversed"

class Payout(Base):
    """
    Tracks payouts/transfers to creators.
    """
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users_creators.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Amount in Naira
    reference = Column(String, unique=True, nullable=False, index=True)
    status = Column(SQLEnum(PayoutStatus), default=PayoutStatus.PENDING)
    
    recipient_code = Column(String, nullable=False)
    transfer_code = Column(String, nullable=True)  # Paystack transfer code (TRF_...)
    
    description = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("UserCreator", backref="payouts")