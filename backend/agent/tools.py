"""Agent tools — functions callable by the Agent via LangChain/LangGraph."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from collector.supervisor import CollectorSupervisor
from analyzer.trend import compute_trend
from analyzer.normalizer import compute_daily_hotness
from repository.hotness import HotnessRepository
from repository.posts import PostRepository

logger = logging.getLogger(__name__)


async def search_topic_hotness(
    topic: str,
    platforms: Optional[str] = None,
    days: int = 7,
    hotness_repo: HotnessRepository | None = None,
    post_repo: PostRepository | None = None,
) -> dict:
    """Query hotness data for a topic across platforms.

    Args:
        topic: Topic name, e.g. "GEO", "Rust", "大模型"
        platforms: Comma-separated platform list, e.g. "xiaohongshu,zhihu"
        days: Number of days to look back

    Returns: {
        "topic": str,
        "platforms": {platform: {"trend": str, "change": float, "data_points": int}},
        "top_posts": list,
    }
    """
    if hotness_repo is None or post_repo is None:
        return {"error": "Repository not available", "topic": topic}

    plat_list = [p.strip() for p in platforms.split(",")] if platforms else None
    result = {"topic": topic, "platforms": {}, "top_posts": []}

    if plat_list is None:
        plat_list = ["bilibili", "xiaohongshu", "zhihu", "github"]

    for plat in plat_list:
        try:
            trend = await compute_trend(hotness_repo, topic, plat, days)
            result["platforms"][plat] = {
                "trend": trend["trend"],
                "change_percent": trend["change_percent"],
                "data_points": len(trend["data"]),
            }
            if not result["top_posts"]:
                posts = await post_repo.get_top_posts(topic, plat, limit=3)
                result["top_posts"] = [
                    {"platform": p.platform, "title": p.title, "url": p.url}
                    for p in posts
                ]
        except Exception as e:
            logger.error(f"Error querying {topic} on {plat}: {e}")
            result["platforms"][plat] = {"error": str(e)}

    return result


async def trigger_collection(
    topic: str,
    platforms: Optional[str] = None,
    supervisor: CollectorSupervisor | None = None,
) -> dict:
    """Trigger data collection for a specific topic.

    Args:
        topic: Topic/keyword to search for
        platforms: Comma-separated platform list, e.g. "bilibili,github"

    Returns: {"status": "ok"|"error", "results": {platform: count}}
    """
    if supervisor is None:
        return {"status": "error", "message": "Collector supervisor not available"}

    plat_list = [p.strip() for p in platforms.split(",")] if platforms else None

    try:
        results = await supervisor.collect_keyword(topic, plat_list)
        return {
            "status": "ok",
            "results": results,
            "total": sum(results.values()),
        }
    except Exception as e:
        logger.error(f"Collection trigger failed for '{topic}': {e}")
        return {"status": "error", "message": str(e)}


async def get_top_topics(
    platform: str,
    limit: int = 10,
    hotness_repo: HotnessRepository | None = None,
) -> dict:
    """Get the current top topics on a platform.

    Args:
        platform: Platform name, e.g. "bilibili", "github"
        limit: Number of topics to return

    Returns: {"platform": str, "topics": list}
    """
    if hotness_repo is None:
        return {"error": "Repository not available", "platform": platform}

    try:
        topics = await hotness_repo.get_top_topics(days=1, limit=limit)
        return {
            "platform": platform,
            "topics": topics,
        }
    except Exception as e:
        logger.error(f"Error getting top topics for {platform}: {e}")
        return {"platform": platform, "topics": [], "error": str(e)}


async def compare_topics(
    topics: str,
    platform: str,
    days: int = 7,
    hotness_repo: HotnessRepository | None = None,
) -> dict:
    """Compare hotness trends between multiple topics on a platform.

    Args:
        topics: Comma-separated topic names
        platform: Platform name
        days: Number of days

    Returns: {"platform": str, "comparison": {topic: trend_data}}
    """
    if hotness_repo is None:
        return {"error": "Repository not available"}

    topic_list = [t.strip() for t in topics.split(",")]
    result = {"platform": platform, "comparison": {}}

    for topic in topic_list:
        try:
            trend = await compute_trend(hotness_repo, topic, platform, days)
            result["comparison"][topic] = {
                "trend": trend["trend"],
                "change_percent": trend["change_percent"],
                "latest_score": trend["data"][-1]["score"] if trend["data"] else 0,
            }
        except Exception as e:
            result["comparison"][topic] = {"error": str(e)}

    return result
