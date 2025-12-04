"""
Instagram Analytics History & Reporting API Endpoints

This module provides FastAPI endpoints for:
1. Analytics history retrieval
2. Growth rate calculations
3. Performance reports
4. Historical trend analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import logging

from database import get_db
from instagram_analytics_history import (
    record_analytics_snapshot,
    get_analytics_history,
    calculate_growth_rate,
    get_peak_performance,
    get_average_metrics,
    cleanup_old_analytics_history,
    generate_analytics_report,
)
from schemas import AnalyticsHistoryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics/history", tags=["Analytics History"])


# ---------------------------
# History Retrieval Endpoints
# ---------------------------

@router.get("/{user_id}", response_model=List[AnalyticsHistoryResponse])
async def get_creator_history(
    user_id: int,
    days: int = Query(30, ge=1, le=365),
    limit: Optional[int] = Query(None, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> List[AnalyticsHistoryResponse]:
    """
    Retrieve analytics history for a creator.
    
    Args:
        user_id: Creator user ID
        days: Number of days to look back (default: 30, max: 365)
        limit: Maximum number of records (optional)
        db: Database session
    
    Returns:
        List of historical analytics records
    """
    try:
        history = await get_analytics_history(db, user_id, days=days, limit=limit)
        return history
    except Exception as e:
        logger.error(f"Error retrieving history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Growth & Trend Analysis
# ---------------------------

@router.get("/{user_id}/growth")
async def get_growth_analysis(
    user_id: int = Path(..., gt=0),
    metric: str = Query("followers_count", regex="^(followers_count|engagement_rate|reach_7d|impressions_7d)$"),
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Calculate growth rate for a specific metric.
    
    Args:
        user_id: Creator user ID
        metric: Metric to analyze (followers_count, engagement_rate, reach_7d, impressions_7d)
        days: Number of days to analyze (default: 30, min: 7, max: 365)
        db: Database session
    
    Returns:
        Growth analysis with absolute and percentage changes
    """
    try:
        growth = await calculate_growth_rate(db, user_id, days=days, metric=metric)
        if not growth:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient data to calculate growth for {metric}"
            )
        
        return growth
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating growth for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/averages")
async def get_average_metrics_endpoint(
    user_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, float]:
    """
    Get average values for all metrics over a period.
    
    Args:
        user_id: Creator user ID
        days: Number of days to analyze (default: 30)
        db: Database session
    
    Returns:
        Dictionary of average metrics
    """
    try:
        averages = await get_average_metrics(db, user_id, days=days)
        if not averages:
            raise HTTPException(
                status_code=404,
                detail="No analytics data found for this creator"
            )
        
        return averages
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating averages for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/peak")
async def get_peak_performance_endpoint(
    user_id: int = Path(..., gt=0),
    metric: str = Query("engagement_rate", regex="^(followers_count|engagement_rate|reach_7d|impressions_7d)$"),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Find peak performance day for a specific metric.
    
    Args:
        user_id: Creator user ID
        metric: Metric to analyze
        days: Number of days to look back (default: 30)
        db: Database session
    
    Returns:
        Peak performance details including the peak value and date
    """
    try:
        peak = await get_peak_performance(db, user_id, days=days, metric=metric)
        if not peak:
            raise HTTPException(
                status_code=404,
                detail=f"No peak performance data found for {metric}"
            )
        
        return peak
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding peak for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Reporting Endpoints
# ---------------------------

@router.get("/{user_id}/report")
async def generate_report(
    user_id: int,
    days: int = Query(30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generate a comprehensive analytics report for a creator.
    
    The report includes:
    - Current metrics snapshot
    - Average metrics over the period
    - Follower growth analysis
    - Engagement rate growth
    - Peak performance metrics
    
    Args:
        user_id: Creator user ID
        days: Number of days to analyze (default: 30, min: 7, max: 365)
        db: Database session
    
    Returns:
        Comprehensive analytics report
    """
    try:
        report = await generate_analytics_report(db, user_id, days=days)
        if not report or "current_metrics" not in report:
            raise HTTPException(
                status_code=404,
                detail="Insufficient data to generate report for this creator"
            )
        
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Batch Reporting
# ---------------------------

@router.get("/batch/reports")
async def generate_batch_reports(
    days: int = Query(30, ge=7, le=365),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Generate reports for multiple creators.
    
    Args:
        days: Number of days to analyze
        limit: Number of creators to include
        db: Database session
    
    Returns:
        List of analytics reports
    """
    try:
        from instagram_analytics_service import get_all_creators_analytics
        
        all_analytics = await get_all_creators_analytics(db, limit=limit)
        reports = []
        
        for analytics in all_analytics:
            user_id = analytics.get("user_id")
            report = await generate_analytics_report(db, user_id, days=days)
            if report:
                reports.append(report)
        
        return reports
    except Exception as e:
        logger.error(f"Error generating batch reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Cleanup & Maintenance
# ---------------------------

@router.post("/maintenance/cleanup")
async def cleanup_old_history(
    days_to_keep: int = Query(365, ge=30, le=1825),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete analytics history older than specified number of days.
    
    This endpoint should be called periodically (e.g., weekly) to maintain
    database performance. Default is to keep 1 year of history.
    
    Args:
        days_to_keep: Number of days of history to retain (default: 365, min: 30, max: 5 years)
        db: Database session
    
    Returns:
        Cleanup summary with number of records deleted
    """
    try:
        deleted_count = await cleanup_old_analytics_history(db, days_to_keep=days_to_keep)
        
        return {
            "status": "success",
            "records_deleted": deleted_count,
            "days_to_keep": days_to_keep,
            "message": f"Deleted {deleted_count} analytics records older than {days_to_keep} days"
        }
    except Exception as e:
        logger.error(f"Error cleaning up history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Comparison Endpoints
# ---------------------------

@router.get("/compare/{user_id1}/{user_id2}")
async def compare_creators(
    user_id1: int,
    user_id2: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Compare analytics between two creators.
    
    Args:
        user_id1: First creator user ID
        user_id2: Second creator user ID
        days: Number of days to compare
        db: Database session
    
    Returns:
        Comparison of metrics between the two creators
    """
    try:
        from instagram_analytics_service import get_creator_analytics
        
        creator1_analytics = await get_creator_analytics(db, user_id1)
        creator2_analytics = await get_creator_analytics(db, user_id2)
        
        if not creator1_analytics or not creator2_analytics:
            raise HTTPException(
                status_code=404,
                detail="One or both creators not found"
            )
        
        comparison = {
            "creator_1": {
                "user_id": user_id1,
                "username": creator1_analytics.data.get("ig_username"),
                "followers": creator1_analytics.followers_count,
                "engagement_rate": creator1_analytics.engagement_rate,
                "reach_7d": creator1_analytics.reach_7d,
            },
            "creator_2": {
                "user_id": user_id2,
                "username": creator2_analytics.data.get("ig_username"),
                "followers": creator2_analytics.followers_count,
                "engagement_rate": creator2_analytics.engagement_rate,
                "reach_7d": creator2_analytics.reach_7d,
            },
            "comparison": {
                "followers_difference": (creator1_analytics.followers_count or 0) - (creator2_analytics.followers_count or 0),
                "engagement_difference": (creator1_analytics.engagement_rate or 0) - (creator2_analytics.engagement_rate or 0),
                "reach_7d_difference": (creator1_analytics.reach_7d or 0) - (creator2_analytics.reach_7d or 0),
            }
        }
        
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing creators: {e}")
        raise HTTPException(status_code=500, detail=str(e))
