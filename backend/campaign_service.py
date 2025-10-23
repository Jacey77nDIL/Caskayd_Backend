import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, func, desc

from models import (
    Campaign, CampaignCreator, UserCreator, UserBusiness, 
    Conversation, Message, CampaignStatus, CreatorCampaignStatus
)
import schemas

logger = logging.getLogger(__name__)
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, func, desc

from models import (
    Campaign, CampaignCreator, UserCreator, UserBusiness, 
    Conversation, Message, CampaignStatus, CreatorCampaignStatus
)
import schemas

logger = logging.getLogger(__name__)


class CampaignService:

    @staticmethod
    async def create_campaign(
        business_id: int,
        data: schemas.CampaignCreate,
        db: AsyncSession
    ) -> Campaign:
        """Create a new campaign"""
        campaign = Campaign(
        business_id=business_id,
        title=data.title,
        description=data.description,
        brief=data.brief,
        brief_file_url=data.brief_file_url, # <-- ADD THIS
        budget=data.budget,
        start_date=data.start_date,
        end_date=data.end_date,
        status=CampaignStatus.DRAFT
    )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign
    
    @staticmethod
    async def get_campaigns(
        business_id: int,
        db: AsyncSession,
        status: Optional[str] = None
    ) -> List[Campaign]:
        """Get all campaigns for a business"""
        query = select(Campaign).where(Campaign.business_id == business_id)
        
        if status:
            query = query.where(Campaign.status == status)
        
        query = query.order_by(desc(Campaign.created_at))
        
        result = await db.execute(query)
        campaigns = result.scalars().all()
        
        # Get creator counts for each campaign
        campaign_list = []
        for campaign in campaigns:
            creators_count_result = await db.execute(
                select(func.count(CampaignCreator.id))
                .where(CampaignCreator.campaign_id == campaign.id)
            )
            creators_count = creators_count_result.scalar() or 0
            
            campaign_data = schemas.CampaignListResponse(
                id=campaign.id,
                title=campaign.title,
                description=campaign.description,
                status=campaign.status,
                budget=campaign.budget,
                creators_count=creators_count,
                created_at=campaign.created_at
            )
            campaign_list.append(campaign_data)
        
        return campaign_list
    
    @staticmethod
    async def get_campaign_detail(
        campaign_id: int,
        business_id: int,
        db: AsyncSession
    ) -> Optional[schemas.CampaignResponse]:
        """Get detailed campaign information"""
        result = await db.execute(
            select(Campaign)
            .options(selectinload(Campaign.campaign_creators).selectinload(CampaignCreator.creator))
            .where(and_(
                Campaign.id == campaign_id,
                Campaign.business_id == business_id
            ))
        )
        campaign = result.scalar()
        
        if not campaign:
            return None
        
        # Build creator list
        creators_list = []
        for cc in campaign.campaign_creators:
            creators_list.append(schemas.CreatorCampaignResponse(
                id=cc.id,
                creator_id=cc.creator_id,
                creator_name=cc.creator.name,
                creator_email=cc.creator.email,
                status=cc.status,
                invited_at=cc.invited_at,
                responded_at=cc.responded_at,
                notes=cc.notes
            ))
        
        return schemas.CampaignResponse(
            id=campaign.id,
            business_id=campaign.business_id,
            title=campaign.title,
            description=campaign.description,
            brief=campaign.brief,
            budget=campaign.budget,
            start_date=campaign.start_date,
            end_date=campaign.end_date,
            status=campaign.status,
            created_at=campaign.created_at,
            updated_at=campaign.updated_at,
            creators_count=len(creators_list),
            creators=creators_list
        )
    
    @staticmethod
    async def update_campaign(
        campaign_id: int,
        business_id: int,
        data: schemas.CampaignUpdate,
        db: AsyncSession
    ) -> Optional[Campaign]:
        """Update campaign details"""
        result = await db.execute(
            select(Campaign).where(and_(
                Campaign.id == campaign_id,
                Campaign.business_id == business_id
            ))
        )
        campaign = result.scalar()
        
        if not campaign:
            return None
        
        # Update fields
        if data.title is not None:
            campaign.title = data.title
        if data.description is not None:
            campaign.description = data.description
        if data.brief is not None:
            campaign.brief = data.brief
        if data.budget is not None:
            campaign.budget = data.budget
        if data.start_date is not None:
            campaign.start_date = data.start_date
        if data.end_date is not None:
            campaign.end_date = data.end_date
        if data.status is not None:
            campaign.status = data.status
        if data.brief is not None:
            campaign.brief = data.brief
        if data.brief_file_url is not None:
            campaign.brief_file_url = data.brief_file_url 
        if data.budget is not None:
            campaign.budget = data.budget
        
        await db.commit()
        await db.refresh(campaign)
        return campaign
    
    @staticmethod
    async def add_creators_to_campaign(
        campaign_id: int,
        business_id: int,
        creator_ids: List[int],
        notes: Optional[str],
        db: AsyncSession
    ) -> List[CampaignCreator]:
        """Add creators to a campaign"""
        # Verify campaign belongs to business
        campaign_result = await db.execute(
            select(Campaign).where(and_(
                Campaign.id == campaign_id,
                Campaign.business_id == business_id
            ))
        )
        campaign = campaign_result.scalar()
        
        if not campaign:
            return []
        
        added_creators = []
        
        for creator_id in creator_ids:
            # Check if creator exists
            creator_result = await db.execute(
                select(UserCreator).where(UserCreator.id == creator_id)
            )
            creator = creator_result.scalar()
            
            if not creator:
                continue
            
            # Check if already added
            existing_result = await db.execute(
                select(CampaignCreator).where(and_(
                    CampaignCreator.campaign_id == campaign_id,
                    CampaignCreator.creator_id == creator_id
                ))
            )
            existing = existing_result.scalar()
            
            if existing:
                continue
            
            # Add creator to campaign
            campaign_creator = CampaignCreator(
                campaign_id=campaign_id,
                creator_id=creator_id,
                status=CreatorCampaignStatus.INVITED,
                notes=notes
            )
            db.add(campaign_creator)
            added_creators.append(campaign_creator)
        
        await db.commit()
        return added_creators
    
    @staticmethod
    async def remove_creator_from_campaign(
        campaign_id: int,
        business_id: int,
        creator_id: int,
        db: AsyncSession
    ) -> bool:
        """Remove a creator from a campaign"""
        # Verify campaign belongs to business
        campaign_result = await db.execute(
            select(Campaign).where(and_(
                Campaign.id == campaign_id,
                Campaign.business_id == business_id
            ))
        )
        campaign = campaign_result.scalar()
        
        if not campaign:
            return False
        
        # Find and update campaign creator
        result = await db.execute(
            select(CampaignCreator).where(and_(
                CampaignCreator.campaign_id == campaign_id,
                CampaignCreator.creator_id == creator_id
            ))
        )
        campaign_creator = result.scalar()
        
        if not campaign_creator:
            return False
        
        campaign_creator.status = CreatorCampaignStatus.REMOVED
        await db.commit()
        return True
    
    @staticmethod
    async def send_brief_to_creators(
        campaign_id: int,
        business_id: int,
        custom_message: Optional[str],
        db: AsyncSession
    ) -> dict:
        """Send campaign brief to all invited creators via chat"""
        # Get campaign with creators
        campaign_result = await db.execute(
            select(Campaign)
            .options(selectinload(Campaign.campaign_creators).selectinload(CampaignCreator.creator))
            .options(selectinload(Campaign.business))
            .where(and_(
                Campaign.id == campaign_id,
                Campaign.business_id == business_id
            ))
        )
        campaign = campaign_result.scalar()
        
        if not campaign:
            return {"success": False, "message": "Campaign not found"}
        
        if not campaign.brief:
            return {"success": False, "message": "Campaign has no brief"}
        
        # Build brief message
        brief_message = f"""
🎯 Campaign Brief: {campaign.title}

{campaign.description}

📋 BRIEF:
{campaign.brief}
"""
        
        if campaign.budget:
            brief_message += f"\n💰 Budget: ${campaign.budget:,.2f}"
        
        if campaign.start_date and campaign.end_date:
            brief_message += f"\n📅 Campaign Period: {campaign.start_date.strftime('%Y-%m-%d')} to {campaign.end_date.strftime('%Y-%m-%d')}"
        
        if custom_message:
            brief_message += f"\n\n💬 Additional Message:\n{custom_message}"
        
        sent_count = 0
        failed_count = 0
        
        # Send to each creator
        for cc in campaign.campaign_creators:
            if cc.status != CreatorCampaignStatus.INVITED:
                continue
            
            try:
                # Check if conversation exists
                existing_conv_result = await db.execute(
                    select(Conversation).where(and_(
                        Conversation.creator_id == cc.creator_id,
                        Conversation.business_id == business_id,
                        Conversation.is_active == True
                    ))
                )
                conversation = existing_conv_result.scalar()
                
                # Create conversation if it doesn't exist
                if not conversation:
                    conversation = Conversation(
                        creator_id=cc.creator_id,
                        business_id=business_id
                    )
                    db.add(conversation)
                    await db.flush()
                
                # Send message
                message = Message(
                    conversation_id=conversation.id,
                    sender_type="business",
                    sender_id=business_id,
                    content=brief_message
                )
                db.add(message)
                
                conversation.updated_at = func.now()
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send brief to creator {cc.creator_id}: {e}")
                failed_count += 1
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Brief sent to {sent_count} creator(s)",
            "sent_count": sent_count,
            "failed_count": failed_count
        }
    
    @staticmethod
    async def delete_campaign(
        campaign_id: int,
        business_id: int,
        db: AsyncSession
    ) -> bool:
        """Delete a campaign"""
        result = await db.execute(
            select(Campaign).where(and_(
                Campaign.id == campaign_id,
                Campaign.business_id == business_id
            ))
        )
        campaign = result.scalar()
        
        if not campaign:
            return False
        
        await db.delete(campaign)
        await db.commit()
        return True

# Global instance
campaign_service = CampaignService()
