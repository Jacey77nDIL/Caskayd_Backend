"""
Analytics History & Archive Service

This module handles storing and retrieving historical analytics snapshots
for trend analysis and performance tracking over time.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import InstagramAnalyticsHistory, InstagramCreatorSocial
from instagram_analytics_service import fetch_instagram_analytics

logger = logging.getLogger(__name__)


async def record_analytics_snapshot(
    db: AsyncSession,
    user_id: int,
    instagram_user_id: str,
    analytics: Dict[str, Any]
) -> InstagramAnalyticsHistory:
    """
    Record a snapshot of analytics for historical tracking.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        instagram_user_id: Instagram user ID
        analytics: Analytics data dictionary
    
    Returns:
        Created analytics history record
    """
    try:
        history = InstagramAnalyticsHistory(
            user_id=user_id,
            instagram_user_id=instagram_user_id,
            followers_count=analytics.get("followers_count"),
            reach_7d=analytics.get("reach_7d"),
            engagement_rate=analytics.get("engagement_rate"),
            impressions_7d=analytics.get("impressions_7d"),
            profile_views_7d=analytics.get("profile_views_7d"),
            website_clicks_7d=analytics.get("website_clicks_7d"),
            saves_7d=analytics.get("saves_7d"),
            shares_7d=analytics.get("shares_7d"),
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(history)
        await db.commit()
        await db.refresh(history)
        
        logger.info(f"Recorded analytics snapshot for user {user_id}")
        return history
    
    except Exception as e:
        logger.error(f"Error recording analytics snapshot: {e}")
        await db.rollback()
        raise


async def get_analytics_history(
    db: AsyncSession,
    user_id: int,
    days: int = 30,
    limit: Optional[int] = None
) -> List[InstagramAnalyticsHistory]:
    """
    Retrieve analytics history for a creator over a specified period.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        days: Number of days to look back
        limit: Maximum number of records
    
    Returns:
        List of historical analytics records
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = (
            select(InstagramAnalyticsHistory)
            .where(
                and_(
                    InstagramAnalyticsHistory.user_id == user_id,
                    InstagramAnalyticsHistory.recorded_at >= cutoff_date
                )
            )
            .order_by(InstagramAnalyticsHistory.recorded_at.asc())
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await db.execute(query)
        history = result.scalars().all()
        
        return history
    
    except Exception as e:
        logger.error(f"Error retrieving analytics history for user {user_id}: {e}")
        return []


async def calculate_growth_rate(
    db: AsyncSession,
    user_id: int,
    days: int = 30,
    metric: str = "followers_count"
) -> Optional[Dict[str, Any]]:
    """
    Calculate growth rate for a specific metric over time.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        days: Number of days to analyze
        metric: Metric to analyze (followers_count, engagement_rate, reach_7d)
    
    Returns:
        Growth analysis or None if insufficient data
    """
    try:
        history = await get_analytics_history(db, user_id, days=days)
        
        if len(history) < 2:
            return None
        
        # Get metric column
        metric_column = getattr(history[0], metric, None)
        if metric_column is None:
            return None
        
        # Get values
        values = []
        dates = []
        for record in history:
            value = getattr(record, metric)
            if value is not None:
                values.append(value)
                dates.append(record.recorded_at)
        
        if len(values) < 2:
            return None
        
        # Calculate growth
        start_value = values[0]
        end_value = values[-1]
        absolute_change = end_value - start_value
        percentage_change = (absolute_change / start_value * 100) if start_value > 0 else 0
        
        # Calculate average change per day
        days_elapsed = (dates[-1] - dates[0]).days
        daily_change = (absolute_change / days_elapsed) if days_elapsed > 0 else 0
        
        return {
            "metric": metric,
            "start_value": start_value,
            "end_value": end_value,
            "absolute_change": absolute_change,
            "percentage_change": round(percentage_change, 2),
            "daily_change": round(daily_change, 2),
            "start_date": dates[0].isoformat(),
            "end_date": dates[-1].isoformat(),
            "total_days": days_elapsed,
        }
    
    except Exception as e:
        logger.error(f"Error calculating growth rate for user {user_id}: {e}")
        return None


async def get_peak_performance(
    db: AsyncSession,
    user_id: int,
    days: int = 30,
    metric: str = "engagement_rate"
) -> Optional[Dict[str, Any]]:
    """
    Find peak performance day for a specific metric.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        days: Number of days to analyze
        metric: Metric to analyze
    
    Returns:
        Peak performance details or None
    """
    try:
        history = await get_analytics_history(db, user_id, days=days)
        
        if not history:
            return None
        
        peak_record = None
        peak_value = None
        
        for record in history:
            value = getattr(record, metric)
            if value is not None:
                if peak_value is None or value > peak_value:
                    peak_value = value
                    peak_record = record
        
        if not peak_record:
            return None
        
        return {
            "metric": metric,
            "peak_value": peak_value,
            "recorded_at": peak_record.recorded_at.isoformat(),
        }
    
    except Exception as e:
        logger.error(f"Error finding peak performance for user {user_id}: {e}")
        return None


async def get_average_metrics(
    db: AsyncSession,
    user_id: int,
    days: int = 30
) -> Optional[Dict[str, float]]:
    """
    Calculate average values for all metrics over a period.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        days: Number of days to analyze
    
    Returns:
        Dictionary of average metrics
    """
    try:
        history = await get_analytics_history(db, user_id, days=days)
        
        if not history:
            return None
        
        metrics = {
            "followers_count": [],
            "reach_7d": [],
            "engagement_rate": [],
            "impressions_7d": [],
            "profile_views_7d": [],
            "website_clicks_7d": [],
            "saves_7d": [],
            "shares_7d": [],
        }
        
        for record in history:
            for metric_name in metrics:
                value = getattr(record, metric_name)
                if value is not None:
                    metrics[metric_name].append(value)
        
        averages = {}
        for metric_name, values in metrics.items():
            if values:
                average = sum(values) / len(values)
                averages[metric_name] = round(average, 2)
        
        return averages if averages else None
    
    except Exception as e:
        logger.error(f"Error calculating average metrics for user {user_id}: {e}")
        return None


async def cleanup_old_analytics_history(
    db: AsyncSession,
    days_to_keep: int = 365
) -> int:
    """
    Delete analytics history older than specified number of days.
    Useful for maintaining database performance and storage.
    
    Args:
        db: Async database session
        days_to_keep: Number of days of history to keep
    
    Returns:
        Number of records deleted
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        result = await db.execute(
            select(InstagramAnalyticsHistory).where(
                InstagramAnalyticsHistory.recorded_at < cutoff_date
            )
        )
        old_records = result.scalars().all()
        count = len(old_records)
        
        for record in old_records:
            await db.delete(record)
        
        await db.commit()
        logger.info(f"Deleted {count} old analytics records")
        
        return count
    
    except Exception as e:
        logger.error(f"Error cleaning up old analytics history: {e}")
        await db.rollback()
        return 0


async def auto_record_analytics_snapshot(
    db: AsyncSession,
    user_id: int,
    social: InstagramCreatorSocial
) -> Optional[InstagramAnalyticsHistory]:
    """
    Automatically record a snapshot when analytics are updated.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        social: InstagramCreatorSocial record
    
    Returns:
        Created history record or None if error
    """
    try:
        if not social.long_lived_token or not social.instagram_user_id:
            return None
        
        # Fetch current analytics
        analytics = await fetch_instagram_analytics(
            db,
            user_id,
            social.instagram_user_id,
            social.long_lived_token
        )
        
        # Record snapshot
        snapshot = await record_analytics_snapshot(
            db,
            user_id,
            social.instagram_user_id,
            analytics
        )
        
        return snapshot
    
    except Exception as e:
        logger.error(f"Error auto-recording analytics snapshot: {e}")
        return None


async def generate_analytics_report(
    db: AsyncSession,
    user_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """
    Generate a comprehensive analytics report for a creator.
    
    Args:
        db: Async database session
        user_id: Creator user ID
        days: Number of days to analyze
    
    Returns:
        Comprehensive report dictionary
    """
    try:
        report = {
            "user_id": user_id,
            "report_date": datetime.now(timezone.utc).isoformat(),
            "analysis_period_days": days,
        }
        
        # Get current metrics
        current = await get_analytics_history(db, user_id, days=0, limit=1)
        if current:
            record = current[0]
            report["current_metrics"] = {
                "followers_count": record.followers_count,
                "reach_7d": record.reach_7d,
                "engagement_rate": record.engagement_rate,
                "impressions_7d": record.impressions_7d,
            }
        
        # Get averages
        averages = await get_average_metrics(db, user_id, days=days)
        report["average_metrics"] = averages
        
        # Get growth rates
        followers_growth = await calculate_growth_rate(
            db, user_id, days=days, metric="followers_count"
        )
        report["followers_growth"] = followers_growth
        
        engagement_growth = await calculate_growth_rate(
            db, user_id, days=days, metric="engagement_rate"
        )
        report["engagement_growth"] = engagement_growth
        
        # Get peak performance
        peak_engagement = await get_peak_performance(
            db, user_id, days=days, metric="engagement_rate"
        )
        report["peak_engagement"] = peak_engagement
        
        return report
    
    except Exception as e:
        logger.error(f"Error generating analytics report for user {user_id}: {e}")
        return {}
