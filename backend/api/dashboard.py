"""Dashboard endpoint — aggregated data for the main page."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.hotness import HotTopic, DashboardResponse
from repository.hotness import HotnessRepository
from repository.posts import PostRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Get aggregated dashboard data.

    Returns top topics, recent posts, and active platforms.
    """
    hotness_repo = HotnessRepository(db)
    post_repo = PostRepository(db)

    # Top topics (aggregated across platforms)
    top_topics_raw = await hotness_repo.get_top_topics(days=1, limit=10)
    hot_topics = [
        HotTopic(topic=t["topic"], score=t["avg_score"])
        for t in top_topics_raw
    ]

    # Recent posts (last 24h)
    recent = await post_repo.query(days=1, limit=10)
    recent_posts = [
        {
            "platform": p.platform,
            "title": p.title,
            "url": p.url,
            "author": p.author,
            "likes": p.like_count,
            "comments": p.comment_count,
        }
        for p in recent
    ]

    # Active platforms
    platform_counts = await post_repo.count_by_platform(days=1)
    active_platforms = list(platform_counts.keys())

    return DashboardResponse(
        hot_topics=hot_topics,
        recent_posts=recent_posts,
        active_platforms=active_platforms or ["github", "bilibili", "xiaohongshu", "zhihu"],
    )
