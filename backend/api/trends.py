"""Trends endpoint — provides hotness trend data for charts."""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.hotness import TrendResponse, TrendDataPoint
from analyzer.trend import compute_trend
from repository.hotness import HotnessRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["trends"])


@router.get("/trends", response_model=TrendResponse)
async def get_trends(
    topic: str = Query(..., description="Topic name, e.g. 'GEO', 'Rust'"),
    platform: Optional[str] = Query(None, description="Platform: bilibili|xiaohongshu|zhihu|github"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
):
    """Get hotness trend data for a topic on a platform.

    Returns time series data suitable for rendering a line chart.
    """
    hotness_repo = HotnessRepository(db)
    trend = await compute_trend(hotness_repo, topic, platform, days)

    data_points = [
        TrendDataPoint(
            date=dp["date"],
            score=dp["score"],
            post_count=dp["post_count"],
        )
        for dp in trend["data"]
    ]

    return TrendResponse(
        topic=topic,
        platform=platform or "all",
        days=days,
        data=data_points,
        trend=trend["trend"],
        change_percent=trend["change_percent"],
    )


@router.get("/topics/hot")
async def get_hot_topics(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get current top hot topics."""
    hotness_repo = HotnessRepository(db)
    topics = await hotness_repo.get_top_topics(days=1, limit=limit)

    # If platform filter is specified, get platform-specific rankings
    if platform:
        yday = date.today() - timedelta(days=1)
        ranked = await hotness_repo.get_ranking(yday, platform, limit)
        topics = [
            {"topic": r.topic, "avg_score": r.hotness_score, "total_posts": r.post_count}
            for r in ranked
        ]

    return {"topics": topics, "platform": platform or "all"}
