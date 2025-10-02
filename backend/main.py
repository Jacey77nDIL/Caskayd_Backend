from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
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
import logging
import requests
import schemas
from fastapi import Query
from recommendation_service import recommendation_service
from models import UserBusiness, Niche, Industry, UserCreator
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any, List

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
FB_APP_ID = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI = "https://caskayd-application.vercel.app/auth/callback/facebook"

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
        result = exchange_token_and_upsert_insights(db, code, authorization)
        return {"status": "ok", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=401, detail=str(ve))
    except Exception as e:
        # Optional: log e
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

