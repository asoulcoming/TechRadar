"""Hotness-related Pydantic schemas."""

from datetime import date
from typing import Optional

from pydantic import BaseModel


class DailyHotnessOut(BaseModel):
    topic: str
    platform: str
    date: date
    hotness_score: float
    post_count: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    top_posts: list[str] = []

    class Config:
        from_attributes = True


class TrendDataPoint(BaseModel):
    date: str
    score: float
    post_count: int = 0


class TrendResponse(BaseModel):
    topic: str
    platform: str
    days: int
    data: list[TrendDataPoint]
    trend: str  # "上升" | "下降" | "平稳"
    change_percent: float


class HotTopic(BaseModel):
    topic: str
    score: float
    change_percent: float = 0.0
    trend: str = "平稳"


class DashboardResponse(BaseModel):
    hot_topics: list[HotTopic]
    recent_posts: list[dict]
    active_platforms: list[str]
