"""
Instagram Analytics Service

This module provides functionality to:
1. Fetch detailed Instagram analytics for creators
2. Store analytics data in the database
3. Track analytics history over time
4. Calculate trends and insights
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import requests

from models import InstagramCreatorSocial, UserCreator
from instagram_creator_socials import (
    FB_GRAPH,
    _get_followers_and_username,
    _reach_7d,
    _engagement_rate
)

logger = logging.getLogger(__name__)

# ---------------------------
# Analytics Models / Helpers
# ---------------------------

class InstagramAnalytics:
    """Data class for Instagram analytics"""
    def __init__(self, data: Dict[str, Any]):
        self.data = data
    
    @property
    def followers_count(self) -> Optional[int]:
        return self.data.get("followers_count")
    
    @property
    def reach_7d(self) -> Optional[int]:
        return self.data.get("reach_7d")
    
    @property
    def engagement_rate(self) -> Optional[float]:
        return self.data.get("engagement_rate")
    
    @property
    def impressions_7d(self) -> Optional[int]:
        return self.data.get("impressions_7d")
    
    @property
    def profile_views_7d(self) -> Optional[int]:
        return self.data.get("profile_views_7d")
    
    @property
    def website_clicks_7d(self) -> Optional[int]:
        return self.data.get("website_clicks_7d")
    
    @property
    def saves_7d(self) -> Optional[int]:
        return self.data.get("saves_7d")
    
    @property
    def shares_7d(self) -> Optional[int]:
        return self.data.get("shares_7d")


# ---------------------------
# Core Analytics Fetching
# ---------------------------

import asyncio
import httpx

# ... (imports)

# ---------------------------
# Core Analytics Fetching
# ---------------------------

async def _get_impressions_7d(ig_user_id: str, token: str) -> Optional[int]:
    """
    Sum last 7 daily values of impressions
    """
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{FB_GRAPH}/{ig_user_id}/insights",
                params={"metric": "impressions", "period": "day", "access_token": token},
                timeout=30,
            )
            r = res.json()
        values = r.get("data", [{}])[0].get("values", [])
        vals = [v.get("value", 0) for v in values][-7:]
        return int(sum(v for v in vals if isinstance(v, (int, float))))
    except Exception as e:
        logger.warning(f"Error fetching impressions for {ig_user_id}: {e}")
        return None


async def _get_profile_views_7d(ig_user_id: str, token: str) -> Optional[int]:
    """
    Sum last 7 daily values of profile views
    """
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{FB_GRAPH}/{ig_user_id}/insights",
                params={"metric": "profile_views", "period": "day", "access_token": token},
                timeout=30,
            )
            r = res.json()
        values = r.get("data", [{}])[0].get("values", [])
        vals = [v.get("value", 0) for v in values][-7:]
        return int(sum(v for v in vals if isinstance(v, (int, float))))
    except Exception as e:
        logger.warning(f"Error fetching profile views for {ig_user_id}: {e}")
        return None


async def _get_website_clicks_7d(ig_user_id: str, token: str) -> Optional[int]:
    """
    Sum last 7 daily values of website clicks (for business accounts with link in bio)
    """
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{FB_GRAPH}/{ig_user_id}/insights",
                params={"metric": "website_clicks", "period": "day", "access_token": token},
                timeout=30,
            )
            r = res.json()
        values = r.get("data", [{}])[0].get("values", [])
        vals = [v.get("value", 0) for v in values][-7:]
        return int(sum(v for v in vals if isinstance(v, (int, float))))
    except Exception as e:
        logger.warning(f"Error fetching website clicks for {ig_user_id}: {e}")
        return None


async def _get_saves_and_shares_7d(ig_user_id: str, token: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Get saves and shares from last 7 posts
    """
    try:
        saves = 0
        shares = 0
        after = None
        fetched = 0
        N = 7

        async with httpx.AsyncClient() as client:
            while fetched < N:
                params = {
                    "fields": "ig_id",
                    "limit": min(25, N - fetched),
                    "access_token": token,
                }
                if after:
                    params["after"] = after
                
                res = await client.get(f"{FB_GRAPH}/{ig_user_id}/media", params=params, timeout=30)
                r = res.json()
                data = r.get("data", [])
                
                # Fetch insights for posts in parallel
                post_insight_tasks = []
                for m in data:
                    ig_id = m.get("ig_id")
                    if ig_id:
                        post_insight_tasks.append(
                            client.get(
                                f"{FB_GRAPH}/{ig_id}/insights",
                                params={
                                    "metric": "saved,shares",
                                    "access_token": token
                                },
                                timeout=30,
                            )
                        )
                
                if post_insight_tasks:
                    insight_responses = await asyncio.gather(*post_insight_tasks, return_exceptions=True)
                    
                    for insights_res in insight_responses:
                        if isinstance(insights_res, Exception):
                            continue
                        try:
                            insights_data = insights_res.json().get("data", [])
                            for insight in insights_data:
                                metric = insight.get("name")
                                value = insight.get("values", [{}])[0].get("value", 0)
                                if metric == "saved":
                                    saves += value
                                elif metric == "shares":
                                    shares += value
                        except Exception:
                            continue

                fetched += len(data)
                after = (r.get("paging") or {}).get("cursors", {}).get("after")
                if not after or not data:
                    break

        return saves if saves > 0 else None, shares if shares > 0 else None
    except Exception as e:
        logger.warning(f"Error fetching saves/shares for {ig_user_id}: {e}")
        return None, None


async def fetch_instagram_analytics(
    db: AsyncSession,
    user_id: int,
    ig_user_id: str,
    token: str
) -> Dict[str, Any]:
    """
    Fetch comprehensive Instagram analytics for a creator.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        ig_user_id: Instagram business account ID
        token: Long-lived access token
    
    Returns:
        Dictionary containing all analytics
    """
    try:
        # Fetch all metrics in parallel
        results = await asyncio.gather(
            _get_followers_and_username(ig_user_id, token),
            _reach_7d(ig_user_id, token),
            _get_impressions_7d(ig_user_id, token),
            _get_profile_views_7d(ig_user_id, token),
            _get_website_clicks_7d(ig_user_id, token),
            _get_saves_and_shares_7d(ig_user_id, token),
        )
        
        (followers, ig_username), reach_7d, impressions_7d, profile_views_7d, website_clicks_7d, (saves_7d, shares_7d) = results
        
        # Engagement rate depends on followers, so we fetch it after or pass followers if we had it.
        # But _engagement_rate needs followers.
        # We can await it separately or chain it.
        engagement_rate = await _engagement_rate(ig_user_id, token, followers)

        analytics = {
            "user_id": user_id,
            "ig_user_id": ig_user_id,
            "ig_username": ig_username,
            "followers_count": followers,
            "reach_7d": reach_7d,
            "engagement_rate": engagement_rate,
            "impressions_7d": impressions_7d,
            "profile_views_7d": profile_views_7d,
            "website_clicks_7d": website_clicks_7d,
            "saves_7d": saves_7d,
            "shares_7d": shares_7d,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Successfully fetched analytics for user {user_id}")
        return analytics

    except Exception as e:
        logger.error(f"Error fetching Instagram analytics for user {user_id}: {e}")
        raise


async def update_creator_analytics(
    db: AsyncSession,
    user_id: int
) -> Optional[Dict[str, Any]]:
    """
    Update analytics for a specific creator by fetching latest data.
    
    Args:
        db: Async database session
        user_id: Creator user ID
    
    Returns:
        Updated analytics or None if not found
    """
    try:
        # Get creator's Instagram social record
        result = await db.execute(
            select(InstagramCreatorSocial).where(
                and_(
                    InstagramCreatorSocial.user_id == user_id,
                    InstagramCreatorSocial.platform == "instagram"
                )
            )
        )
        social = result.scalar_one_or_none()

        if not social or not social.long_lived_token or not social.instagram_user_id:
            logger.warning(f"No valid Instagram account found for user {user_id}")
            return None

        # Fetch fresh analytics
        analytics = await fetch_instagram_analytics(
            db,
            user_id,
            social.instagram_user_id,
            social.long_lived_token
        )

        # Update the database record
        social.followers_count = analytics.get("followers_count")
        social.reach_7d = analytics.get("reach_7d")
        social.engagement_rate = analytics.get("engagement_rate")
        social.insights_last_updated_at = datetime.now(timezone.utc)

        await db.commit()

        return analytics

    except Exception as e:
        logger.error(f"Error updating analytics for user {user_id}: {e}")
        raise


async def get_creator_analytics(
    db: AsyncSession,
    user_id: int
) -> Optional[InstagramAnalytics]:
    """
    Retrieve stored analytics for a creator from the database.
    
    Args:
        db: Async database session
        user_id: Creator user ID
    
    Returns:
        InstagramAnalytics object or None if not found
    """
    try:
        result = await db.execute(
            select(InstagramCreatorSocial).where(
                and_(
                    InstagramCreatorSocial.user_id == user_id,
                    InstagramCreatorSocial.platform == "instagram"
                )
            )
        )
        social = result.scalar_one_or_none()

        if not social:
            return None

        analytics_data = {
            "user_id": social.user_id,
            "ig_user_id": social.instagram_user_id,
            "ig_username": social.instagram_username,
            "followers_count": social.followers_count,
            "reach_7d": social.reach_7d,
            "engagement_rate": social.engagement_rate,
            "insights_last_updated_at": social.insights_last_updated_at.isoformat()
            if social.insights_last_updated_at else None,
        }

        return InstagramAnalytics(analytics_data)

    except Exception as e:
        logger.error(f"Error retrieving analytics for user {user_id}: {e}")
        return None


async def get_all_creators_analytics(
    db: AsyncSession,
    limit: Optional[int] = None,
    offset: Optional[int] = 0
) -> List[Dict[str, Any]]:
    """
    Retrieve analytics for all creators.
    
    Args:
        db: Async database session
        limit: Maximum number of results
        offset: Number of results to skip
    
    Returns:
        List of analytics dictionaries
    """
    try:
        query = select(InstagramCreatorSocial).where(
            InstagramCreatorSocial.platform == "instagram"
        ).order_by(InstagramCreatorSocial.insights_last_updated_at.desc())

        if limit:
            query = query.limit(limit).offset(offset or 0)

        result = await db.execute(query)
        socials = result.scalars().all()

        analytics_list = []
        for social in socials:
            analytics_data = {
                "user_id": social.user_id,
                "ig_username": social.instagram_username,
                "followers_count": social.followers_count,
                "reach_7d": social.reach_7d,
                "engagement_rate": social.engagement_rate,
                "insights_last_updated_at": social.insights_last_updated_at.isoformat()
                if social.insights_last_updated_at else None,
            }
            analytics_list.append(analytics_data)

        return analytics_list

    except Exception as e:
        logger.error(f"Error retrieving all creators analytics: {e}")
        return []


async def get_top_creators_by_metric(
    db: AsyncSession,
    metric: str = "followers_count",
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get top creators sorted by a specific metric.
    
    Args:
        db: Async database session
        metric: Metric to sort by (followers_count, engagement_rate, reach_7d)
        limit: Number of results to return
    
    Returns:
        List of top creators
    """
    try:
        if metric not in ["followers_count", "engagement_rate", "reach_7d"]:
            raise ValueError(f"Invalid metric: {metric}")

        metric_column = getattr(InstagramCreatorSocial, metric)
        query = (
            select(InstagramCreatorSocial)
            .where(
                and_(
                    InstagramCreatorSocial.platform == "instagram",
                    metric_column.isnot(None)
                )
            )
            .order_by(metric_column.desc())
            .limit(limit)
        )

        result = await db.execute(query)
        socials = result.scalars().all()

        top_creators = []
        for social in socials:
            creator_data = {
                "user_id": social.user_id,
                "ig_username": social.instagram_username,
                "followers_count": social.followers_count,
                "engagement_rate": social.engagement_rate,
                "reach_7d": social.reach_7d,
                metric: getattr(social, metric),
            }
            top_creators.append(creator_data)

        return top_creators

    except Exception as e:
        logger.error(f"Error fetching top creators by {metric}: {e}")
        return []


async def get_analytics_trends(
    db: AsyncSession,
    user_id: int,
    days: int = 7
) -> Optional[Dict[str, Any]]:
    """
    Get analytics trends for a creator over a specified period.
    Note: This requires storing historical analytics data.
    For now, it returns the current snapshot.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        days: Number of days to look back
    
    Returns:
        Trends analysis or None
    """
    try:
        result = await db.execute(
            select(InstagramCreatorSocial).where(
                and_(
                    InstagramCreatorSocial.user_id == user_id,
                    InstagramCreatorSocial.platform == "instagram"
                )
            )
        )
        social = result.scalar_one_or_none()

        if not social:
            return None

        trends = {
            "user_id": user_id,
            "ig_username": social.instagram_username,
            "current_followers": social.followers_count,
            "current_reach_7d": social.reach_7d,
            "current_engagement_rate": social.engagement_rate,
            "last_updated": social.insights_last_updated_at.isoformat()
            if social.insights_last_updated_at else None,
        }

        return trends

    except Exception as e:
        logger.error(f"Error calculating trends for user {user_id}: {e}")
        return None


# ---------------------------
# Batch Operations
# ---------------------------

async def refresh_all_creator_analytics(db: AsyncSession) -> Dict[str, Any]:
    """
    Refresh analytics for all creators with valid tokens.
    
    Args:
        db: Async database session
    
    Returns:
        Summary of the refresh operation
    """
    summary = {
        "total_updated": 0,
        "total_failed": 0,
        "failed_users": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        result = await db.execute(
            select(InstagramCreatorSocial).where(
                and_(
                    InstagramCreatorSocial.platform == "instagram",
                    InstagramCreatorSocial.long_lived_token.isnot(None),
                    InstagramCreatorSocial.instagram_user_id.isnot(None)
                )
            )
        )
        socials = result.scalars().all()

        for social in socials:
            try:
                await update_creator_analytics(db, social.user_id)
                summary["total_updated"] += 1
            except Exception as e:
                logger.error(f"Failed to update analytics for user {social.user_id}: {e}")
                summary["total_failed"] += 1
                summary["failed_users"].append(social.user_id)

        summary["completed_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as e:
        logger.error(f"Error in batch refresh: {e}")

    return summary
