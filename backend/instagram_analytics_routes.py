"""
Instagram Analytics API Endpoints

This module provides FastAPI endpoints for:
1. Fetching and updating creator analytics
2. Retrieving analytics history and trends
3. Getting top performers
4. Managing batch operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import logging

from database import get_db
from auth import decode_user_id_from_jwt
from instagram_analytics_service import (
    fetch_instagram_analytics,
    update_creator_analytics,
    get_creator_analytics,
    get_all_creators_analytics,
    get_top_creators_by_metric,
    get_analytics_trends,
    refresh_all_creator_analytics,
)
from schemas import (
    InstagramAnalyticsResponse,
    TopCreatorResponse,
    AnalyticsTrendsResponse,
    BatchRefreshResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Instagram Analytics"])

# ---------------------------
# Analytics Endpoints
# ---------------------------

@router.get("/instagram/{user_id}", response_model=InstagramAnalyticsResponse)
async def get_instagram_analytics(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> InstagramAnalyticsResponse:
    """
    Get current Instagram analytics for a creator.
    
    Args:
        user_id: Creator user ID
        db: Database session
    
    Returns:
        Current analytics data
    """
    try:
        analytics = await get_creator_analytics(db, user_id)
        if not analytics:
            raise HTTPException(status_code=404, detail="No Instagram analytics found for this creator")
        
        return {
            "user_id": user_id,
            "ig_user_id": analytics.data.get("ig_user_id"),
            "ig_username": analytics.data.get("ig_username"),
            "followers_count": analytics.followers_count,
            "reach_7d": analytics.reach_7d,
            "engagement_rate": analytics.engagement_rate,
            "impressions_7d": analytics.impressions_7d,
            "profile_views_7d": analytics.profile_views_7d,
            "website_clicks_7d": analytics.website_clicks_7d,
            "saves_7d": analytics.saves_7d,
            "shares_7d": analytics.shares_7d,
            "insights_last_updated_at": analytics.data.get("insights_last_updated_at"),
        }
    except Exception as e:
        logger.error(f"Error fetching analytics for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instagram/{user_id}/refresh")
async def refresh_instagram_analytics(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> InstagramAnalyticsResponse:
    """
    Refresh Instagram analytics for a specific creator.
    Fetches latest data from Instagram and updates the database.
    
    Args:
        user_id: Creator user ID
        db: Database session
    
    Returns:
        Updated analytics data
    """
    try:
        analytics = await update_creator_analytics(db, user_id)
        if not analytics:
            raise HTTPException(
                status_code=404,
                detail="Creator not found or no valid Instagram account connected"
            )
        
        return InstagramAnalyticsResponse(**analytics)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing analytics for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instagram/all/list")
async def list_all_analytics(
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[InstagramAnalyticsResponse]:
    """
    Get analytics for all creators.
    
    Args:
        limit: Maximum number of results (default: all)
        offset: Number of results to skip
        db: Database session
    
    Returns:
        List of analytics for all creators
    """
    try:
        analytics_list = await get_all_creators_analytics(db, limit=limit, offset=offset)
        return analytics_list
    except Exception as e:
        logger.error(f"Error fetching all analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instagram/top/{metric}")
async def get_top_creators(
    metric: str = Path(..., regex="^(followers_count|engagement_rate|reach_7d)$"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[TopCreatorResponse]:
    """
    Get top creators sorted by a specific metric.
    
    Args:
        metric: Metric to sort by (followers_count, engagement_rate, reach_7d)
        limit: Number of results to return
        db: Database session
    
    Returns:
        List of top creators
    """
    try:
        top_creators = await get_top_creators_by_metric(db, metric=metric, limit=limit)
        return top_creators
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching top creators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/instagram/{user_id}/trends")
async def get_creator_trends(
    user_id: int,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsTrendsResponse:
    """
    Get analytics trends for a creator.
    
    Args:
        user_id: Creator user ID
        days: Number of days to analyze
        db: Database session
    
    Returns:
        Trends analysis
    """
    try:
        trends = await get_analytics_trends(db, user_id, days=days)
        if not trends:
            raise HTTPException(
                status_code=404,
                detail="No trends data found for this creator"
            )
        
        return trends
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trends for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instagram/batch/refresh")
async def batch_refresh_analytics(
    db: AsyncSession = Depends(get_db),
) -> BatchRefreshResponse:
    """
    Refresh analytics for all creators with valid Instagram accounts.
    This is a heavy operation and should be called periodically (e.g., via a scheduler).
    
    Args:
        db: Database session
    
    Returns:
        Summary of the batch operation
    """
    try:
        summary = await refresh_all_creator_analytics(db)
        return BatchRefreshResponse(**summary)
    except Exception as e:
        logger.error(f"Error in batch refresh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Health Check
# ---------------------------

@router.get("/health")
async def health_check():
    """Health check endpoint for the analytics service"""
    return {"status": "healthy", "service": "instagram_analytics"}
