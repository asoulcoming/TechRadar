"""Trend calculation utilities."""

from datetime import date, timedelta
from typing import Optional

from repository.hotness import HotnessRepository


async def compute_trend(
    hotness_repo: HotnessRepository,
    topic: str,
    platform: Optional[str] = None,
    days: int = 30,
) -> dict:
    """Compute trend data for a topic.

    Returns: {
        "data": list of {date, score, post_count},
        "trend": "上升" | "下降" | "平稳",
        "change_percent": float,
    }
    """
    records = await hotness_repo.get_trend(topic, platform, days)

    data_points = [
        {
            "date": str(r.date),
            "score": r.hotness_score,
            "post_count": r.post_count,
        }
        for r in records
    ]

    # Compute trend direction
    if len(data_points) >= 7:
        first_week_avg = sum(p["score"] for p in data_points[:7]) / 7
        last_week_avg = sum(p["score"] for p in data_points[-7:]) / 7

        if first_week_avg > 0:
            change = ((last_week_avg - first_week_avg) / first_week_avg) * 100
        else:
            change = 100 if last_week_avg > 0 else 0
    elif len(data_points) >= 2:
        first_half = sum(p["score"] for p in data_points[:len(data_points)//2]) / (len(data_points)//2)
        second_half = sum(p["score"] for p in data_points[len(data_points)//2:]) / (len(data_points) - len(data_points)//2)
        if first_half > 0:
            change = ((second_half - first_half) / first_half) * 100
        else:
            change = 100 if second_half > 0 else 0
    else:
        change = 0.0

    if change > 20:
        trend = "显著上升"
    elif change > 5:
        trend = "小幅上升"
    elif change > -5:
        trend = "平稳"
    elif change > -20:
        trend = "小幅下降"
    else:
        trend = "显著下降"

    return {
        "data": data_points,
        "trend": trend,
        "change_percent": round(change, 1),
    }
