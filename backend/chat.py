import logging
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, or_, desc, func
from database import get_db
from models import UserCreator, UserBusiness, Conversation, Message
import models
import schemas
from typing import List, Optional
logger = logging.getLogger(__name__)
class ChatService:
    
    @staticmethod
    async def get_user_by_email_and_role(email: str, role: str,  db: AsyncSession = Depends(get_db)):
        """Get user by email and role"""
        if role == "creator":
            result = await db.execute(select(UserCreator).where(UserCreator.email == email))
            return result.scalar(), "creator"
        elif role == "business":
            result = await db.execute(select(UserBusiness).where(UserBusiness.email == email))
            return result.scalar(), "business"
        return None, None
    
    @staticmethod
    async def create_conversation(current_user_email: str, current_user_role: str, 
                                data: schemas.ConversationCreate, db: AsyncSession = Depends(get_db)):
        """Create a new conversation between business and creator"""
        
        
        if current_user_role != "business":
            return None
            
        
        business_result = await db.execute(select(UserBusiness).where(UserBusiness.email == current_user_email))
        business = business_result.scalar()
        if not business:
            return None
            
       
        creator_result = await db.execute(select(UserCreator).where(UserCreator.email == data.creator_email))
        creator = creator_result.scalar()
        if not creator:
            return None
        if not business or not creator:
            print("DEBUG: UserBusiness ->", business, "UserCreator ->", creator)
            return None
        
            
        
        existing = await db.execute(
            select(Conversation).where(
                and_(
                    Conversation.creator_id == creator.id,
                    Conversation.business_id == business.id,
                    Conversation.is_active == True
                )
            )
        )
        if existing.scalar():
            return None  
        conversation = Conversation(
            creator_id=creator.id,
            business_id=business.id
        )
        db.add(conversation)
        await db.flush()
        
        
        initial_message = Message(
            conversation_id=conversation.id,
            sender_type="business",
            sender_id=business.id,
            content=data.initial_message
        )
        db.add(initial_message)
        await db.commit()
        
        return conversation.id
    
    @staticmethod
    async def get_conversations(current_user_email: str, current_user_role: str, 
                              db: AsyncSession = Depends(get_db)) -> List[schemas.ConversationResponse]:
        """Get all conversations for the current user"""
        
        user, role = await ChatService.get_user_by_email_and_role(current_user_email, current_user_role, db)
        if not user:
            return []
            
        
        if role == "creator":
            query = select(Conversation).where(
                and_(Conversation.creator_id == user.id, Conversation.is_active == True)
            ).options(
                selectinload(Conversation.business),
                selectinload(Conversation.creator)
            ).order_by(desc(Conversation.updated_at))
        else:  # business
            query = select(Conversation).where(
                and_(Conversation.business_id == user.id, Conversation.is_active == True)
            ).options(
                selectinload(Conversation.business),
                selectinload(Conversation.creator)
            ).order_by(desc(Conversation.updated_at))
            
        result = await db.execute(query)
        conversations = result.scalars().all()
        
        
        conversation_responses = []
        for conv in conversations:
            
            last_msg_query = select(Message).where(
                Message.conversation_id == conv.id
            ).order_by(desc(Message.created_at)).limit(1)
            last_msg_result = await db.execute(last_msg_query)
            last_msg = last_msg_result.scalar()
            
            
            unread_query = select(func.count(Message.id)).where(
                and_(
                    Message.conversation_id == conv.id,
                    Message.is_read == False,
                    or_(
                        and_(Message.sender_type == "creator", role == "business"),
                        and_(Message.sender_type == "business", role == "creator")
                    )
                )
            )
            unread_result = await db.execute(unread_query)
            unread_count = unread_result.scalar() or 0
            
            conversation_responses.append(schemas.ConversationResponse(
                id=conv.id,
                creator_id=conv.creator_id,
                business_id=conv.business_id,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                is_active=conv.is_active,
                creator_email=conv.creator.email,
                business_name=conv.business.business_name,
                last_message=last_msg.content if last_msg else None,
                last_message_time=last_msg.created_at if last_msg else None,
                unread_count=unread_count
            ))
            
        return conversation_responses
    
    @staticmethod
    async def get_conversation_detail(conversation_id: int, current_user_email: str, 
                                    current_user_role: str, db: AsyncSession = Depends(get_db)) -> Optional[schemas.ConversationDetail]:
        """Get detailed conversation with messages"""
        
        user, role = await ChatService.get_user_by_email_and_role(current_user_email, current_user_role, db)
        if not user:
            return None
            
        
        query = select(Conversation).where(Conversation.id == conversation_id).options(
            selectinload(Conversation.business),
            selectinload(Conversation.creator),
            selectinload(Conversation.messages)
        )
        result = await db.execute(query)
        conversation = result.scalar()
        
        if not conversation:
            return None
            
        
        if role == "creator" and conversation.creator_id != user.id:
            return None
        elif role == "business" and conversation.business_id != user.id:
            return None
        
        other_sender_type = "creator" if current_user_role == "business" else "business"
        
        messages_query = select(Message).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_type == other_sender_type,
                Message.is_read == False
            )
        )
        result = await db.execute(messages_query)
        messages = result.scalars().all()
        
        for message in messages:
            message.is_read = True
            
        await db.commit()
    
    @staticmethod
    async def get_creators_list(db: AsyncSession = Depends(get_db)) -> List[dict]:
        """Get list of all creators for businesses to start conversations with"""
        
        result = await db.execute(select(UserCreator))
        creators = result.scalars().all()
        
        return [{"email": creator.email, "id": creator.id} for creator in creators]