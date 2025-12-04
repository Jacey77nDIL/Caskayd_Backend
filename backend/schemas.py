from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
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
    content: Optional[str] = None 
    file_url: Optional[str] = None
    file_type: Optional[str] = None

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

from pydantic import BaseModel
from typing import Optional

class PaymentInitialize(BaseModel):
    amount: float  # Amount in Naira (will be converted to kobo)
    currency: str = "NGN"
    callback_url: Optional[str] = None
    purpose: Optional[str] = None
    metadata: Optional[dict] = None

class PaymentInitializeResponse(BaseModel):
    status: bool
    authorization_url: str
    access_code: str
    reference: str

class PaymentVerifyResponse(BaseModel):
    status: bool
    transaction_status: str
    reference: str
    amount: float
    currency: str
    paid_at: Optional[str] = None

class CampaignStatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CreatorCampaignStatusEnum(str, Enum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REMOVED = "removed"

class CampaignCreate(BaseModel):
    title: str
    description: str
    brief: Optional[str] = None
    brief_file_url: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    brief: Optional[str] = None
    brief_file_url: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[CampaignStatusEnum] = None

class CampaignCreatorAdd(BaseModel):
    creator_ids: List[int]
    notes: Optional[str] = None

class CampaignBriefSend(BaseModel):
    campaign_id: int
    custom_message: Optional[str] = None

class CreatorCampaignResponse(BaseModel):
    id: int
    creator_id: int
    creator_name: str
    creator_email: str
    status: CreatorCampaignStatusEnum
    invited_at: datetime
    responded_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class CampaignResponse(BaseModel):
    id: int
    business_id: int
    title: str
    description: str
    brief: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: CampaignStatusEnum
    created_at: datetime
    updated_at: datetime
    creators_count: int = 0
    creators: List[CreatorCampaignResponse] = []
    
    class Config:
        from_attributes = True

class CampaignListResponse(BaseModel):
    id: int
    title: str
    description: str
    status: CampaignStatusEnum
    budget: Optional[float] = None
    creators_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class CampaignCreatorFilters(BaseModel):
    """
    Filters for finding creators, to be passed
    during campaign creation.
    """
    location: Optional[str] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    niche_ids: List[int] = []

class CampaignCreateWithFilters(CampaignCreate):
    """
    A new schema for the endpoint that includes
    the campaign data AND the targeting filters.
    """
    filters: CampaignCreatorFilters

class SimpleCreator(BaseModel):
    """
    A simplified creator schema for the
    recommendation list.
    """
    id: int
    name: str
    bio: Optional[str] = None
    followers_count: Optional[int] = 0
    engagement_rate: Optional[str] = "N/A"
    instagram_username: Optional[str] = None
    niches: List[Dict[str, Any]] = []

class CampaignCreateResponse(BaseModel):
    """
    The new response model for the POST /campaigns endpoint.
    """
    campaign: CampaignResponse
    recommendations: List[SimpleCreator]

# --- Add these classes to schemas.py ---

class TikTokAuthUrlResponse(BaseModel):
    authorization_url: str

class TikTokAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None 


class PresignedUrlRequest(BaseModel):
    file_name: str
    file_type: str 


class InstagramAnalyticsResponse(BaseModel):
    """Response schema for Instagram analytics"""
    user_id: int
    ig_user_id: Optional[str] = None
    ig_username: Optional[str] = None
    followers_count: Optional[int] = None
    reach_7d: Optional[int] = None
    engagement_rate: Optional[float] = None
    impressions_7d: Optional[int] = None
    profile_views_7d: Optional[int] = None
    website_clicks_7d: Optional[int] = None
    saves_7d: Optional[int] = None
    shares_7d: Optional[int] = None
    insights_last_updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class AnalyticsHistoryResponse(BaseModel):
    """Response schema for analytics history"""
    id: int
    user_id: int
    followers_count: Optional[int] = None
    reach_7d: Optional[int] = None
    engagement_rate: Optional[float] = None
    impressions_7d: Optional[int] = None
    profile_views_7d: Optional[int] = None
    website_clicks_7d: Optional[int] = None
    saves_7d: Optional[int] = None
    shares_7d: Optional[int] = None
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class TopCreatorResponse(BaseModel):
    """Response schema for top creators by metric"""
    user_id: int
    ig_username: Optional[str] = None
    followers_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    reach_7d: Optional[int] = None
    
    class Config:
        from_attributes = True


class AnalyticsTrendsResponse(BaseModel):
    """Response schema for analytics trends"""
    user_id: int
    ig_username: Optional[str] = None
    current_followers: Optional[int] = None
    current_reach_7d: Optional[int] = None
    current_engagement_rate: Optional[float] = None
    last_updated: Optional[str] = None

class CampaignStatusEnum(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class CreatorCampaignStatusEnum(str, Enum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REMOVED = "removed"

class CampaignCreate(BaseModel):
    title: str
    description: str
    brief: Optional[str] = None
    brief_file_url: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    brief: Optional[str] = None
    brief_file_url: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[CampaignStatusEnum] = None

class CampaignCreatorAdd(BaseModel):
    creator_ids: List[int]
    notes: Optional[str] = None

class CampaignBriefSend(BaseModel):
    campaign_id: int
    custom_message: Optional[str] = None

class CreatorCampaignResponse(BaseModel):
    id: int
    creator_id: int
    creator_name: str
    creator_email: str
    status: CreatorCampaignStatusEnum
    invited_at: datetime
    responded_at: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class CampaignResponse(BaseModel):
    id: int
    business_id: int
    title: str
    description: str
    brief: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: CampaignStatusEnum
    created_at: datetime
    updated_at: datetime
    creators_count: int = 0
    creators: List[CreatorCampaignResponse] = []
    
    class Config:
        from_attributes = True

class CampaignListResponse(BaseModel):
    id: int
    title: str
    description: str
    status: CampaignStatusEnum
    budget: Optional[float] = None
    creators_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class CampaignCreatorFilters(BaseModel):
    """
    Filters for finding creators, to be passed
    during campaign creation.
    """
    location: Optional[str] = None
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    niche_ids: List[int] = []

class CampaignCreateWithFilters(CampaignCreate):
    """
    A new schema for the endpoint that includes
    the campaign data AND the targeting filters.
    """
    filters: CampaignCreatorFilters

class SimpleCreator(BaseModel):
    """
    A simplified creator schema for the
    recommendation list.
    """
    id: int
    name: str
    bio: Optional[str] = None
    followers_count: Optional[int] = 0
    engagement_rate: Optional[str] = "N/A"
    instagram_username: Optional[str] = None
    niches: List[Dict[str, Any]] = []

class CampaignCreateResponse(BaseModel):
    """
    The new response model for the POST /campaigns endpoint.
    """
    campaign: CampaignResponse
    recommendations: List[SimpleCreator]

# --- Add these classes to schemas.py ---

class TikTokAuthUrlResponse(BaseModel):
    authorization_url: str

class TikTokAuthCallback(BaseModel):
    code: str
    state: Optional[str] = None 


class PresignedUrlRequest(BaseModel):
    file_name: str
    file_type: str 


class InstagramAnalyticsResponse(BaseModel):
    """Response schema for Instagram analytics"""
    user_id: int
    ig_user_id: Optional[str] = None
    ig_username: Optional[str] = None
    followers_count: Optional[int] = None
    reach_7d: Optional[int] = None
    engagement_rate: Optional[float] = None
    impressions_7d: Optional[int] = None
    profile_views_7d: Optional[int] = None
    website_clicks_7d: Optional[int] = None
    saves_7d: Optional[int] = None
    shares_7d: Optional[int] = None
    insights_last_updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class AnalyticsHistoryResponse(BaseModel):
    """Response schema for analytics history"""
    id: int
    user_id: int
    followers_count: Optional[int] = None
    reach_7d: Optional[int] = None
    engagement_rate: Optional[float] = None
    impressions_7d: Optional[int] = None
    profile_views_7d: Optional[int] = None
    website_clicks_7d: Optional[int] = None
    saves_7d: Optional[int] = None
    shares_7d: Optional[int] = None
    recorded_at: datetime
    
    class Config:
        from_attributes = True


class TopCreatorResponse(BaseModel):
    """Response schema for top creators by metric"""
    user_id: int
    ig_username: Optional[str] = None
    followers_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    reach_7d: Optional[int] = None
    
    class Config:
        from_attributes = True


class AnalyticsTrendsResponse(BaseModel):
    """Response schema for analytics trends"""
    user_id: int
    ig_username: Optional[str] = None
    current_followers: Optional[int] = None
    current_reach_7d: Optional[int] = None
    current_engagement_rate: Optional[float] = None
    last_updated: Optional[str] = None
    
    class Config:
        from_attributes = True


class BatchRefreshResponse(BaseModel):
    """Response schema for batch analytics refresh"""
    total_updated: int
    total_failed: int
    failed_users: List[int] = []
    started_at: str
    completed_at: Optional[str] = None

# --- Payout / Bank Schemas ---

class BankAccountCreate(BaseModel):
    account_number: str
    bank_code: str

class BankAccountResponse(BaseModel):
    id: int
    account_number: str
    account_name: str
    bank_name: str
    bank_code: str
    currency: str
    
    class Config:
        from_attributes = True

class BankListResponse(BaseModel):
    name: str
    code: str
    active: bool

class PayoutRequest(BaseModel):
    amount: float  # Amount in Naira
    description: Optional[str] = "Payout"

class PayoutResponse(BaseModel):
    reference: str
    amount: float
    status: str
    transfer_code: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True