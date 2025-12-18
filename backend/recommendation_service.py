import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import and_, or_, func, desc, asc, text
from models import (
    UserCreator, UserBusiness, Niche, Industry, BusinessCreatorInteraction, 
    RecommendationCache, creator_niches, business_industries, industry_niches,
    InstagramCreatorSocial
)

class RecommendationService:
    def __init__(self):
        self.cache_duration_minutes = 30  # Cache recommendations for 30 minutes
        self.batch_size = 50  # Process creators in batches of 50
    
    async def get_recommendations(
        self,
        business_id: int,
        db: AsyncSession,
        search_query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        offset: int = 0,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get creator recommendations for a business with caching and pagination
        """
        filters = filters or {}
        
        # Create cache key
        cache_key = self._create_cache_key(business_id, search_query, filters)
        
        # Try to get from cache first
        cached_ids = await self._get_from_cache(business_id, cache_key, db)
        
        if cached_ids:
            # Get creators from cached IDs with pagination
            return await self._get_creators_by_ids(
                cached_ids[offset:offset + limit], db
            )
        
        # Generate new recommendations
        creator_ids = await self._generate_recommendations(
            business_id, db, search_query, filters
        )
        
        # Cache the results
        await self._cache_recommendations(
            business_id, cache_key, creator_ids, db
        )
        
        # Return paginated results
        return await self._get_creators_by_ids(
            creator_ids[offset:offset + limit], db
        )
    
    async def _generate_recommendations(
        self,
        business_id: int,
        db: AsyncSession,
        search_query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[int]:
        """
        Generate creator recommendations based on business industries and filters
        """
        # Get business industries
        business_result = await db.execute(
            select(UserBusiness)
            .options(selectinload(UserBusiness.industries).selectinload(Industry.niches))
            .where(UserBusiness.id == business_id)
        )
        business = business_result.scalar()
        
        if not business or not business.industries:
            return []
        
        # Get all relevant niches for business industries
        relevant_niche_ids = []
        for industry in business.industries:
            relevant_niche_ids.extend([niche.id for niche in industry.niches])
        
        # Get previously viewed creators to deprioritize them
        viewed_creators_result = await db.execute(
            select(BusinessCreatorInteraction.creator_id)
            .where(BusinessCreatorInteraction.business_id == business_id)
            .distinct()
        )
        viewed_creator_ids = [row[0] for row in viewed_creators_result.fetchall()]
        
        # Build base query - join with Instagram socials to get follower data
        query = (
            select(
                UserCreator.id, 
                func.count(creator_niches.c.niche_id).label('niche_match_count'),
                func.max(InstagramCreatorSocial.followers_count).label('followers_count'),
                func.max(InstagramCreatorSocial.engagement_rate).label('engagement_rate')
            )
            .join(creator_niches, UserCreator.id == creator_niches.c.creator_id)
            .outerjoin(InstagramCreatorSocial, UserCreator.id == InstagramCreatorSocial.user_id)
            .where(creator_niches.c.niche_id.in_(relevant_niche_ids))
            .group_by(UserCreator.id)
        )
        
        # Apply search filter if provided
        if search_query:
            search_filter = or_(
                UserCreator.name.ilike(f"%{search_query}%"),
                UserCreator.bio.ilike(f"%{search_query}%")
            )
            query = query.where(search_filter)
        
        # Apply other filters
        if filters:
            query = await self._apply_filters(query, filters)
        
        # Order by: search relevance (if search), niche matches, then by recency, with viewed creators last
        if search_query:
            # Prioritize exact name matches, then partial matches
            query = query.order_by(
                desc(func.similarity(UserCreator.name, search_query)),
                desc(text('niche_match_count')),
                desc(UserCreator.created_at)
            )
        else:
            query = query.order_by(
                desc(text('niche_match_count')),
                desc(UserCreator.created_at)
            )
        
        # Execute query in batches to avoid overwhelming the database
        fresh_creator_ids = []
        viewed_creator_ids_ordered = []
        
        result = await db.execute(query)
        for row in result.fetchall():
            creator_id = row[0]  # First column is UserCreator.id
            if creator_id in viewed_creator_ids:
                viewed_creator_ids_ordered.append(creator_id)
            else:
                fresh_creator_ids.append(creator_id)
        
        # Combine: fresh creators first, then viewed creators
        all_creator_ids = fresh_creator_ids + viewed_creator_ids_ordered
        
        return all_creator_ids
    
    async def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply various filters to the creator query"""
        
        # Note: No location filter since it's not in your UserCreator model
        
        if 'min_followers' in filters and filters['min_followers']:
            query = query.where(InstagramCreatorSocial.followers_count >= filters['min_followers'])
        
        if 'max_followers' in filters and filters['max_followers']:
            query = query.where(InstagramCreatorSocial.followers_count <= filters['max_followers'])
        
        if 'engagement_rate' in filters and filters['engagement_rate']:
            query = query.where(InstagramCreatorSocial.engagement_rate >= filters['engagement_rate'])
        
        if 'niches' in filters and filters['niches']:
            # Additional niche filtering
            niche_ids = filters['niches']
            query = query.where(creator_niches.c.niche_id.in_(niche_ids))
        
        return query
    
    async def _get_creators_by_ids(self, creator_ids: List[int], db: AsyncSession) -> List[Dict]:
        """Get creator details by IDs maintaining order"""
        if not creator_ids:
            return []
        
        result = await db.execute(
            select(UserCreator)
            .options(
                selectinload(UserCreator.niches),
                selectinload(UserCreator.socials)
            )
            .where(UserCreator.id.in_(creator_ids))
        )
        creators_dict = {creator.id: creator for creator in result.scalars()}
        
        # Return creators in the same order as creator_ids
        ordered_creators = []
        for creator_id in creator_ids:
            if creator_id in creators_dict:
                creator = creators_dict[creator_id]
                
                # Get Instagram social data if available
                instagram_social = None
                for social in creator.socials:
                    if social.platform == "instagram":
                        instagram_social = social
                        break
                
                creator_data = {
                    'id': creator.id,
                    'name': creator.name,
                    'bio': creator.bio,
                    'email': creator.email,  # You might want to hide this in production
                    'followers_count': instagram_social.followers_count if instagram_social else 0,
                    'engagement_rate': f"{instagram_social.engagement_rate}%" if instagram_social and instagram_social.engagement_rate else "N/A",
                    'instagram_username': instagram_social.instagram_username if instagram_social else None,
                    'reach_7d': instagram_social.reach_7d if instagram_social else None,
                    'niches': [{'id': niche.id, 'name': niche.name} for niche in creator.niches],
                    'created_at': creator.created_at.isoformat() if creator.created_at else None
                }
                ordered_creators.append(creator_data)
        
        return ordered_creators
    
    def _create_cache_key(self, business_id: int, search_query: Optional[str], filters: Dict[str, Any]) -> str:
        """Create a unique cache key for the recommendation parameters"""
        cache_data = {
            'search_query': search_query or '',
            'filters': filters
        }
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    async def _get_from_cache(self, business_id: int, cache_key: str, db: AsyncSession) -> Optional[List[int]]:
        """Get cached recommendations if they exist and are not expired"""
        result = await db.execute(
            select(RecommendationCache)
            .where(
                and_(
                    RecommendationCache.business_id == business_id,
                    RecommendationCache.cache_key == cache_key,
                    RecommendationCache.expires_at > datetime.utcnow()
                )
            )
        )
        cache_entry = result.scalar()
        
        if cache_entry:
            # Update last_accessed
            cache_entry.last_accessed = datetime.utcnow()
            await db.commit()
            
            return json.loads(cache_entry.creator_ids)
        
        return None
    
    async def _cache_recommendations(self, business_id: int, cache_key: str, creator_ids: List[int], db: AsyncSession):
        """Cache the recommendation results"""
        # Clean up old cache entries for this business (keep only recent 10)
        old_entries_result = await db.execute(
            select(RecommendationCache)
            .where(RecommendationCache.business_id == business_id)
            .order_by(desc(RecommendationCache.created_at))
            .offset(10)
        )
        old_entries = old_entries_result.scalars().all()
        
        for entry in old_entries:
            await db.delete(entry)
        
        # Create new cache entry
        cache_entry = RecommendationCache(
            business_id=business_id,
            cache_key=cache_key,
            creator_ids=json.dumps(creator_ids),
            expires_at=datetime.utcnow() + timedelta(minutes=self.cache_duration_minutes)
        )
        
        db.add(cache_entry)
        await db.commit()
    
    async def mark_creator_viewed(self, business_id: int, creator_id: int, db: AsyncSession):
        """Mark a creator as viewed by a business"""
        # Check if interaction already exists
        existing_result = await db.execute(
            select(BusinessCreatorInteraction)
            .where(
                and_(
                    BusinessCreatorInteraction.business_id == business_id,
                    BusinessCreatorInteraction.creator_id == creator_id
                )
            )
        )
        
        if not existing_result.scalar():
            interaction = BusinessCreatorInteraction(
                business_id=business_id,
                creator_id=creator_id,
                interaction_type='viewed'
            )
            db.add(interaction)
            await db.commit()
    
    async def invalidate_cache(self, business_id: int, db: AsyncSession):
        """Invalidate all cached recommendations for a business"""
        result = await db.execute(
            select(RecommendationCache)
            .where(RecommendationCache.business_id == business_id)
        )
        cache_entries = result.scalars().all()
        
        for entry in cache_entries:
            await db.delete(entry)
        
        await db.commit()

# Global instance
recommendation_service = RecommendationService()