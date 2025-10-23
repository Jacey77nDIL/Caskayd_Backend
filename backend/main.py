from datetime import datetime, timezone
import uuid
from fastapi import FastAPI, Depends, HTTPException, Request, Header, logger
from fastapi.middleware.cors import CORSMiddleware
import httpx
from sqlalchemy import and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
import campaign_service
from paystack_service import paystack_service
from database import Base, get_db, engine
import models, auth
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import os
from chat import ChatService
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from websocket_ import manager
from sqlalchemy.future import select
from models import Conversation
from sqlalchemy.orm import selectinload
from models import UserCreator
from sqlalchemy.future import select
from passlib.context import CryptContext
from instagram_creator_socials import InstagramCreatorSocial, exchange_token_and_upsert_insights
import requests
import schemas
from fastapi import Query
from recommendation_service import recommendation_service
from models import UserBusiness, Niche, Industry, UserCreator
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any, List
import uuid
import tiktok_service
from auth import decode_jwt_from_header, decode_user_id_from_jwt
from fastapi import Header
import logging
from cloudflare_service import cloudflare_service

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
FB_APP_ID = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI = "https://caskayd-application.vercel.app/auth/callback/facebook"
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.on_event("startup")
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
    

# --- In main.py, inside @app.post("/auth/facebook") ---

@app.post("/auth/facebook")
async def facebook_auth(
    request: Request,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Body: { "code": "<facebook_code>" }
    Header: Authorization: Bearer <your_user_jwt>
    """
    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing 'code' in body.")

    try:
        # 1. You can still use the new helpers for validation (good)
        payload = decode_jwt_from_header(authorization)
        user, role = await decode_user_id_from_jwt(payload, db)
        
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can link Facebook accounts")

        from instagram_creator_socials import exchange_token_and_upsert_insights
        
        # 2. THE FIX: Pass the original 'authorization' string, NOT the 'payload'
        result = exchange_token_and_upsert_insights(db, code, authorization) 

        return {"status": "ok", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=401, detail=str(ve))
    except Exception as e:
        logger.error(f"Facebook auth error: {e}") # Use your logger
        raise HTTPException(status_code=500, detail=f"Auth/Insights failed: {e}")

@app.get("/chat/creators", response_model=List[dict])
async def get_creators(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """Get list of creators for businesses to start conversations with"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can access creators list")
            
        creators = await ChatService.get_creators_list(db)
        return creators
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/chat/conversations")
async def create_conversation(
    data: schemas.ConversationCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        conversation_id = await ChatService.create_conversation(email, role, data, db)
        if not conversation_id:
            raise HTTPException(status_code=400, detail="Failed to create conversation")
            
        return {"conversation_id": conversation_id, "message": "Conversation created successfully"}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/chat/conversations", response_model=List[schemas.ConversationResponse])
async def get_conversations(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        conversations = await ChatService.get_conversations(email, role, db)
        return conversations
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/chat/conversations/{conversation_id}", response_model=schemas.ConversationDetail)
async def get_conversation_detail(
    conversation_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed conversation with messages"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        conversation = await ChatService.get_conversation_detail(conversation_id, email, role, db)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
        return conversation
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/chat/messages", response_model=schemas.MessageResponse)
async def send_message(
    data: schemas.MessageCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Send a message in a conversation"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        message = await ChatService.send_message(email, role, data, db)
        if not message:
            raise HTTPException(status_code=400, detail="Failed to send message")
            
        return message
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.put("/chat/conversations/{conversation_id}/read")
async def mark_conversation_as_read(
    conversation_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Mark all messages in a conversation as read"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        
        await ChatService.mark_messages_as_read(conversation_id, role, db)
        return {"message": "Messages marked as read"}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    



@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time chat"""
    
    if not await manager.connect(websocket, token):
        return
    
    try:
        while True:
           
            data = await websocket.receive_text()
           
            await websocket.send_text(f"pong: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/chat/messages", response_model=schemas.MessageResponse)
async def send_message_with_notifications(
    data: schemas.MessageCreate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Send a message in a conversation with real-time notifications"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        message = await ChatService.send_message(email, role, data, db)
        if not message:
            raise HTTPException(status_code=400, detail="Failed to send message")
        
        
        conversation_query = select(Conversation).where(
            Conversation.id == data.conversation_id
        ).options(
            selectinload(Conversation.creator),
            selectinload(Conversation.business)
        )
        conv_result = await db.execute(conversation_query)
        conversation = conv_result.scalar()
        
        if conversation:
            
            notification = {
                "type": "new_message",
                "conversation_id": conversation.id,
                "message": {
                    "id": message.id,
                    "sender_type": message.sender_type,
                    "sender_id": message.sender_id,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                    "is_read": message.is_read
                },
                "conversation_info": {
                    "creator_email": conversation.creator.email,
                    "business_name": conversation.business.business_name
                }
            }
            
            await manager.send_to_conversation_participants(
                conversation.creator.email,
                conversation.business.email,
                conversation.business.business_name,
                notification
            )
        
        return message
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@app.get("/recommendations")
async def get_creator_recommendations(
    search: Optional[str] = Query(None, description="Search query for creator name or bio"),
    location: Optional[str] = Query(None, description="Filter by creator location"),
    min_followers: Optional[int] = Query(None, description="Minimum follower count"),
    max_followers: Optional[int] = Query(None, description="Maximum follower count"),
    engagement_rate: Optional[float] = Query(None, description="Minimum engagement rate (as percentage, e.g., 4.5)"),
    niches: Optional[str] = Query(None, description="Comma-separated niche IDs"),
    offset: int = Query(0, description="Pagination offset", ge=0),
    limit: int = Query(5, description="Number of results to return", ge=1, le=20),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Verify token and get business info
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can access recommendations")
        
        # Get business ID
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="UserBusiness not found")
        
        
        filters = {}
        if location:
            filters['location'] = location
        if min_followers is not None:
            filters['min_followers'] = min_followers
        if max_followers is not None:
            filters['max_followers'] = max_followers
        if engagement_rate is not None:
            filters['engagement_rate'] = engagement_rate
        if niches:
            try:
                niche_ids = [int(niche_id.strip()) for niche_id in niches.split(',')]
                filters['niches'] = niche_ids
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid niche IDs format")
        
        recommendations = await recommendation_service.get_recommendations(
            business_id=business.id,
            db=db,
            search_query=search,
            filters=filters,
            offset=offset,
            limit=limit
        )
        
        return {
            "success": True,
            "data": {
                "recommendations": recommendations,
                "pagination": {
                    "offset": offset,
                    "limit": limit,
                    "returned_count": len(recommendations),
                    "has_more": len(recommendations) == limit
                }
            },
            "message": f"Found {len(recommendations)} creator recommendations"
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/recommendations/mark-viewed/{creator_id}")
async def mark_creator_viewed(
    creator_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a creator as viewed by the current business.
    This affects future recommendation ordering (viewed creators appear later).
    """
    try:
        # Verify token and get business info
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can mark creators as viewed")
        
        # Get business ID
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="UserBusiness not found")
        
        # Verify creator exists
        creator_result = await db.execute(
            select(UserCreator).where(UserCreator.id == creator_id)
        )
        creator = creator_result.scalar()
        
        if not creator:
            raise HTTPException(status_code=404, detail="UserCreator not found")
   
        await recommendation_service.mark_creator_viewed(business.id, creator_id, db)
        
        return {
            "success": True,
            "message": f"UserCreator {creator.name} marked as viewed",
            "data": {
                "creator_id": creator_id,
                "creator_name": creator.name
            }
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/recommendations/filters/niches")
async def get_available_niches(
    db: AsyncSession = Depends(get_db)
):
   
    try:
        result = await db.execute(
            select(Niche).order_by(Niche.name)
        )
        niches = result.scalars().all()
        
        return {
            "success": True,
            "data": {
                "niches": [
                    {
                        "id": niche.id,
                        "name": niche.name
                    } for niche in niches
                ]
            },
            "message": f"Found {len(niches)} available niches"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/recommendations/filters/industries")
async def get_available_industries(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available industries with their associated niches.
    Useful for understanding industry-niche mappings.
    """
    try:
        result = await db.execute(
            select(Industry)
            .options(selectinload(Industry.niches))
            .order_by(Industry.name)
        )
        industries = result.scalars().all()
        
        return {
            "success": True,
            "data": {
                "industries": [
                    {
                        "id": industry.id,
                        "name": industry.name,
                        "niches": [
                            {
                                "id": niche.id,
                                "name": niche.name
                            } for niche in industry.niches
                        ]
                    } for industry in industries
                ]
            },
            "message": f"Found {len(industries)} available industries"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/recommendations/stats")
async def get_recommendation_stats(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    
    try:
       
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can view stats")
        
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="UserBusiness not found")
        
        from models import BusinessCreatorInteraction
        viewed_count_result = await db.execute(
            select(func.count(BusinessCreatorInteraction.id.distinct()))
            .where(BusinessCreatorInteraction.business_id == business.id)
        )
        viewed_count = viewed_count_result.scalar() or 0
        
        
        from models import RecommendationCache
        cache_count_result = await db.execute(
            select(func.count(RecommendationCache.id))
            .where(
                and_(
                    RecommendationCache.business_id == business.id,
                    RecommendationCache.expires_at > datetime.utcnow()
                )
            )
        )
        cache_count = cache_count_result.scalar() or 0
        
        # Get total creators available
        total_creators_result = await db.execute(
            select(func.count(UserCreator.id))
        )
        total_creators = total_creators_result.scalar() or 0
        
        return {
            "success": True,
            "data": {
                "viewed_creators_count": viewed_count,
                "active_cache_entries": cache_count,
                "total_creators_available": total_creators,
                "business_info": {
                    "id": business.id,
                    "name": business.business_name,
                    "email": business.email
                }
            },
            "message": "Recommendation statistics retrieved successfully"
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/recommendations/cache")
async def clear_recommendation_cache(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Clear all cached recommendations for the current business.
    Useful for testing or when you want fresh recommendations immediately.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can clear cache")
        
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="UserBusiness not found")
        
        await recommendation_service.invalidate_cache(business.id, db)
        
        return {
            "success": True,
            "message": "Recommendation cache cleared successfully",
            "data": {
                "business_id": business.id,
                "cleared_at": datetime.utcnow().isoformat()
            }
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/profile/creator/setup")
async def setup_creator_profile(
    profile_data: schemas.CreatorProfileSetup,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    try:
       
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can set up profiles")
        
        
        creator_result = await db.execute(
            select(UserCreator)
            .options(selectinload(UserCreator.niches))
            .where(UserCreator.email == email)
        )
        creator = creator_result.scalar_one_or_none()
                
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
        
        
        creator.name = profile_data.name
      
        if profile_data.bio:
            creator.bio = profile_data.bio
        
    
        if profile_data.location:
            creator.location = profile_data.location
        
       
        if profile_data.followers_count is not None:
            creator.followers_count = profile_data.followers_count
        
       
        if profile_data.engagement_rate is not None:
           
            engagement_str = profile_data.engagement_rate.strip('%')
            creator.engagement_rate = float(engagement_str)
        
        
        if profile_data.profile_image:
            creator.profile_image = profile_data.profile_image
        
       
        if profile_data.niche_ids:
          
            niche_results = await db.execute(
                select(Niche).where(Niche.id.in_(profile_data.niche_ids))
            )
            valid_niches = niche_results.scalars().all()
            
            # Verify all requested niches exist
            if len(valid_niches) != len(profile_data.niche_ids):
                found_ids = {niche.id for niche in valid_niches}
                missing_ids = set(profile_data.niche_ids) - found_ids
                raise HTTPException(
                    status_code=400, 
                    detail=f"Niche IDs not found: {missing_ids}"
                )
            
            # Assign the list of Niche objects directly to the relationship
            creator.niches = valid_niches
        
    
        if profile_data.followers_count is not None or profile_data.engagement_rate is not None:
            social_result = await db.execute(
                select(InstagramCreatorSocial).where(InstagramCreatorSocial.user_id == creator.id)
            )
            social = social_result.scalar_one_or_none()
            
            if social:
                
                if profile_data.followers_count is not None:
                    social.followers_count = profile_data.followers_count
                if profile_data.engagement_rate is not None:
                    engagement_str = profile_data.engagement_rate.strip('%')
                    social.engagement_rate = float(engagement_str)
                social.insights_last_updated_at = datetime.now(timezone.utc)
            else:
                
                social = InstagramCreatorSocial(
                    user_id=creator.id,
                    platform="instagram",
                    followers_count=profile_data.followers_count,
                    engagement_rate=float(profile_data.engagement_rate.strip('%')) if profile_data.engagement_rate else None,
                    insights_last_updated_at=datetime.now(timezone.utc)
                )
                db.add(social)
            
        await db.commit()
        await db.refresh(creator) 
        response_data = {
            "id": creator.id,
            "name": creator.name,
            "email": creator.email,
            "bio": creator.bio,
            "location": creator.location,
            "followers_count": creator.followers_count,
            "engagement_rate": creator.engagement_rate,
            "profile_image": creator.profile_image,
            "niches": [
                {"id": niche.id, "name": niche.name} 
                for niche in creator.niches
            ]
        }
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": {
                "creator": response_data
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        await db.rollback()
        logging.error(f"Error updating creator profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")


@app.post("/profile/business/setup")
async def setup_business_profile(
    industry_ids: List[int],
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Set up business profile with industries.
    This determines which creators appear in recommendations.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can set up business profiles")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness)
            .options(selectinload(UserBusiness.industries))
            .where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="UserBusiness not found")
        
        # Clear existing industries
        business.industries.clear()
        
        # Add new industries
        for industry_id in industry_ids:
            industry_result = await db.execute(
                select(Industry).where(Industry.id == industry_id)
            )
            industry = industry_result.scalar()
            if industry:
                business.industries.append(industry)
            else:
                raise HTTPException(status_code=400, detail=f"Industry with ID {industry_id} not found")
        
        await db.commit()
        
        # Clear cache since business industry changed
        await recommendation_service.invalidate_cache(business.id, db)
        
        return {
            "success": True,
            "message": "UserBusiness profile updated successfully",
            "data": {
                "business": {
                    "id": business.id,
                    "business_name": business.business_name,
                    "email": business.email,
                    "industries": [{"id": industry.id, "name": industry.name} for industry in business.industries]
                }
            }
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
@app.get("/niches")
async def get_available_niches(db: AsyncSession = Depends(get_db)):
    """
    Get all available niches for filtering and profile setup.
    """
    try:
        result = await db.execute(
            select(Niche).order_by(Niche.name)
        )
        niches = result.scalars().all()
        
        return {
            "success": True,
            "data": {
                "niches": [{"id": niche.id, "name": niche.name} for niche in niches]
            },
            "message": f"Found {len(niches)} available niches"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/industries")
async def get_available_industries(db: AsyncSession = Depends(get_db)):
    """
    Get all available industries with their associated niches.
    """
    try:
        result = await db.execute(
            select(Industry)
            .options(selectinload(Industry.niches))
            .order_by(Industry.name)
        )
        industries = result.scalars().all()
        
        return {
            "success": True,
            "data": {
                "industries": [
                    {
                        "id": industry.id,
                        "name": industry.name,
                        "niches": [
                            {"id": niche.id, "name": niche.name} 
                            for niche in industry.niches
                        ]
                    } for industry in industries
                ]
            },
            "message": f"Found {len(industries)} available industries"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/creator/profile")
async def get_creator_profile(db: AsyncSession = Depends(get_db)):
     try:
        result = await db.execute(
            select(UserCreator)
            .order_by(UserCreator.name)
        )
        creators = result.scalars().all()
        
        return {
            "success": True,
            "data": {
                "creators": [
                    {
                        "id": creator.id,
                        "name": creator.name,
                    } for creator in creators
                ]
            },
            "message": f"Found {len(creators)} available industries"
        }
        
     except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/payments/initialize")
async def initialize_payment(
    payment_data: schemas.PaymentInitialize,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Initialize a payment transaction
    Amount should be in Naira (e.g., 5000 for ₦5,000)
    """
    try:
        # Verify token and get user info
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user ID
        if role == "creator":
            user_result = await db.execute(
                select(UserCreator).where(UserCreator.email == email)
            )
            user = user_result.scalar()
        else:
            user_result = await db.execute(
                select(UserBusiness).where(UserBusiness.email == email)
            )
            user = user_result.scalar()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate unique reference
        reference = f"TXN-{uuid.uuid4().hex[:16].upper()}"
        
        # Convert amount from Naira to kobo (multiply by 100)
        amount_in_kobo = int(payment_data.amount * 100)
        
        # Add user info to metadata
        metadata = payment_data.metadata or {}
        metadata.update({
            "user_id": user.id,
            "user_type": role,
            "user_email": email,
            "purpose": payment_data.purpose or "general"
        })
        
        # Initialize payment with Paystack
        result = await paystack_service.initialize_transaction(
            email=email,
            amount=amount_in_kobo,
            currency=payment_data.currency,
            reference=reference,
            callback_url=payment_data.callback_url,
            metadata=metadata
        )
        
        # Save transaction to database
        from models import Transaction, TransactionStatus
        transaction = Transaction(
            reference=reference,
            amount=payment_data.amount,
            currency=payment_data.currency,
            email=email,
            user_id=user.id,
            user_type=role,
            status=TransactionStatus.pending,
            authorization_url=result["authorization_url"],
            access_code=result["access_code"],
            purpose=payment_data.purpose,
            transaction_metadata=metadata  # Changed from metadata
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        return {
            "success": True,
            "message": "Payment initialized successfully",
            "data": {
                "authorization_url": result["authorization_url"],
                "access_code": result["access_code"],
                "reference": reference,
                "amount": payment_data.amount,
                "currency": payment_data.currency
            }
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        await db.rollback()
        logging.error(f"Payment initialization error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")


@app.get("/payments/verify/{reference}")
async def verify_payment(
    reference: str,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Verify a payment transaction
    """
    try:
        # Verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get transaction from database
        from models import Transaction, TransactionStatus
        transaction_result = await db.execute(
            select(Transaction).where(Transaction.reference == reference)
        )
        transaction = transaction_result.scalar()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Verify with Paystack
        result = await paystack_service.verify_transaction(reference)
        
        # Update transaction status
        if result["transaction_status"] == "success":
            transaction.status = TransactionStatus.success
            transaction.paid_at = datetime.now(timezone.utc)
        elif result["transaction_status"] == "failed":
            transaction.status = TransactionStatus.failed
        else:
            transaction.status = TransactionStatus.abandoned
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Payment verification successful",
            "data": {
                "reference": result["reference"],
                "status": result["transaction_status"],
                "amount": result["amount"] / 100,  # Convert from kobo to Naira
                "currency": result["currency"],
                "paid_at": result["paid_at"],
                "customer": result["customer"]
            }
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logging.error(f"Payment verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


@app.get("/payments/history")
async def get_payment_history(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment history for the current user
    """
    try:
        # Verify token and get user info
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user ID
        if role == "creator":
            user_result = await db.execute(
                select(UserCreator).where(UserCreator.email == email)
            )
            user = user_result.scalar()
        else:
            user_result = await db.execute(
                select(UserBusiness).where(UserBusiness.email == email)
            )
            user = user_result.scalar()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get transactions
        from models import Transaction
        transactions_result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by((Transaction.created_at))
        )
        transactions = transactions_result.scalars().all()
        
        return {
            "success": True,
            "message": f"Found {len(transactions)} transactions",
            "data": {
                "transactions": [
                    {
                        "id": t.id,
                        "reference": t.reference,
                        "amount": t.amount,
                        "currency": t.currency,
                        "status": t.status.value,
                        "purpose": t.purpose,
                        "paid_at": t.paid_at.isoformat() if t.paid_at else None,
                        "created_at": t.created_at.isoformat()
                    }
                    for t in transactions
                ]
            }
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logging.error(f"Error fetching payment history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch payment history: {str(e)}")


@app.post("/payments/webhook")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Paystack webhook events
    Paystack will send notifications here when payment status changes
    """
    try:
        import hmac
        import hashlib
        
        # Get the signature from headers
        signature = request.headers.get("x-paystack-signature")
        
        # Get the raw body
        body = await request.body()
        
        # Verify the signature
        computed_signature = hmac.new(
            PAYSTACK_SECRET.encode('utf-8'),
            body,
            hashlib.sha512
        ).hexdigest()
        
        if signature != computed_signature:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse the event
        event = await request.json()
        event_type = event.get("event")
        data = event.get("data", {})
        
        # Handle charge.success event
        if event_type == "charge.success":
            reference = data.get("reference")
            
            # Update transaction in database
            from models import Transaction, TransactionStatus
            transaction_result = await db.execute(
                select(Transaction).where(Transaction.reference == reference)
            )
            transaction = transaction_result.scalar()
            
            if transaction:
                transaction.status = TransactionStatus.success
                transaction.paid_at = datetime.now(timezone.utc)
                await db.commit()
                
                logging.info(f"Payment successful for reference: {reference}")
                
                # TODO: Add custom logic here (e.g., send email, update subscription)
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
    

@app.post("/campaigns", response_model=schemas.CampaignCreateResponse)
async def create_campaign(
    data: schemas.CampaignCreateWithFilters,  # <--- THE FIX IS HERE
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new campaign and get initial creator recommendations.
    (Business only)
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can create campaigns")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        # Create the base campaign data object for the service
        campaign_data = schemas.CampaignCreate(
            title=data.title,
            description=data.description,
            brief=data.brief,
            brief_file_url=data.brief_file_url,
            budget=data.budget,
            start_date=data.start_date,
            end_date=data.end_date
        )
        
        # --- Call Campaign Service ---
        # Note: We call campaign_service.campaign_service (file.instance.method)
        campaign = await campaign_service.campaign_service.create_campaign(
            business.id, campaign_data, db
        )
        
        # Get the full campaign detail for the response
        campaign_detail = await campaign_service.campaign_service.get_campaign_detail(
            campaign.id, business.id, db
        )
        
        # --- Call Recommendation Service ---
        
        # Convert the filters object to the dict the service expects
        filter_dict = data.filters.model_dump(exclude_unset=True)
        
        # Rename 'niche_ids' to 'niches' for the service
        if 'niche_ids' in filter_dict:
             filter_dict['niches'] = filter_dict.pop('niche_ids')

        recommendations_list = await recommendation_service.get_recommendations(
            business_id=business.id,
            db=db,
            search_query=None,
            filters=filter_dict,
            offset=0,
            limit=10 
        )
        
        # --- Return the combined response ---
        return schemas.CampaignCreateResponse(
            campaign=campaign_detail,
            recommendations=recommendations_list
        )
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        await db.rollback() 
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/campaigns", response_model=List[schemas.CampaignListResponse])
async def get_campaigns_endpoint(
    status: Optional[str] = Query(None, description="Filter by campaign status"),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get all campaigns for the authenticated business"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can view campaigns")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        campaigns = await campaign_service.get_campaigns(business.id, db, status)
        
        return campaigns
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/campaigns/{campaign_id}", response_model=schemas.CampaignResponse)
async def get_campaign_detail_endpoint(
    campaign_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a campaign"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can view campaign details")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        campaign = await campaign_service.get_campaign_detail(campaign_id, business.id, db)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return campaign
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.put("/campaigns/{campaign_id}", response_model=schemas.CampaignResponse)
async def update_campaign_endpoint(
    campaign_id: int,
    data: schemas.CampaignUpdate,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Update a campaign"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can update campaigns")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        campaign = await campaign_service.update_campaign(campaign_id, business.id, data, db)
        
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        # Return updated campaign detail
        campaign_detail = await campaign_service.get_campaign_detail(campaign.id, business.id, db)
        
        return campaign_detail
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/campaigns/{campaign_id}/creators")
async def add_creators_to_campaign_endpoint(
    campaign_id: int,
    data: schemas.CampaignCreatorAdd,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Add creators to a campaign"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can add creators to campaigns")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        added_creators = await campaign_service.campaign_service.add_creators_to_campaign(
            campaign_id, business.id, data.creator_ids, data.notes, db
        )
        
        return {
            "success": True,
            "message": f"Added {len(added_creators)} creator(s) to campaign",
            "added_count": len(added_creators)
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/campaigns/{campaign_id}/creators/{creator_id}")
async def remove_creator_from_campaign_endpoint(
    campaign_id: int,
    creator_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Remove a creator from a campaign"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can remove creators from campaigns")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        success = await campaign_service.remove_creator_from_campaign(
            campaign_id, business.id, creator_id, db
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Creator not found in campaign")
        
        return {
            "success": True,
            "message": "Creator removed from campaign"
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/campaigns/{campaign_id}/send-brief")
async def send_campaign_brief_endpoint(
    campaign_id: int,
    data: schemas.CampaignBriefSend,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Send campaign brief to all invited creators via chat"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can send campaign briefs")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        result = await campaign_service.send_brief_to_creators(
            campaign_id, business.id, data.custom_message, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        
        return result
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/campaigns/{campaign_id}")
async def delete_campaign_endpoint(
    campaign_id: int,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Delete a campaign"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")
        
        if role != "business":
            raise HTTPException(status_code=403, detail="Only businesses can delete campaigns")
        
        # Get business
        business_result = await db.execute(
            select(UserBusiness).where(UserBusiness.email == email)
        )
        business = business_result.scalar()
        
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
        
        success = await campaign_service.delete_campaign(campaign_id, business.id, db)
        
        if not success:
            raise HTTPException(status_code=404, detail="Campaign not found")
        
        return {
            "success": True,
            "message": "Campaign deleted successfully"
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

@app.get("/auth/tiktok/start", response_model=schemas.TikTokAuthUrlResponse)
async def start_tiktok_auth(token: str = Depends(oauth2_scheme)):
    """
    Get the URL to redirect a creator to for TikTok authentication.
    """
    try:
        # We just need to validate the token is real
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        
        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can link TikTok accounts")
            
        # Create a unique state value for security
        state = str(uuid.uuid4())
        # In a real app, you might save this state in Redis or
        # the user's session to verify it on callback.
        
        url = tiktok_service.tiktok_service.get_authorization_url(state)
        return {"authorization_url": url}
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Service error: {str(e)}")


# --- In main.py ---

@app.post("/auth/tiktok/callback")
async def handle_tiktok_auth_callback(
    data: schemas.TikTokAuthCallback,
    authorization: str = Header(None), 
    db: AsyncSession = Depends(get_db)
):
    try:
        # --- THIS IS THE CORRECT LOGIC ---
        
        # 1. Call this function ONCE with the 'authorization' string
        payload = decode_jwt_from_header(authorization) 
        
        # 2. Use the 'payload' dict in the NEXT function
        user, role = await decode_user_id_from_jwt(payload, db) 
        
        # -----------------------------------
        # DO NOT DO THIS (This is wrong and causes your error):
        # payload = decode_jwt_from_header(authorization)
        # payload = decode_jwt_from_header(payload) # <--- WRONG
        # -----------------------------------

        if role != "creator":
            raise HTTPException(status_code=403, detail="Only creators can link TikTok accounts")
        
        result = await tiktok_service.tiktok_service.exchange_code_and_upsert_data(
            db=db,
            code=data.code,
            creator_user_id=user.id
        )
        
        return {"status": "ok", "data": result}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"TikTok callback error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    

@app.post("/uploads/presigned-url")
async def get_presigned_upload_url(
    data: schemas.PresignedUrlRequest,
    token: str = Depends(oauth2_scheme) # Protect the endpoint
):
    """
    Generates a presigned URL for the client to upload a file to Cloudflare R2.
    """
    try:
        # Just ensure the user is logged in
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        result = cloudflare_service.generate_presigned_upload_url(
            file_name=data.file_name,
            file_type=data.file_type
        )
        if not result:
            raise HTTPException(status_code=500, detail="Could not generate upload URL.")
            
        return result
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))