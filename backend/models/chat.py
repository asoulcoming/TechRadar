"""Chat and Agent-related Pydantic schemas."""

from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChartData(BaseModel):
    type: str = "line"
    title: str = ""
    xAxis: list[str] = []
    series: list[dict] = []


class Source(BaseModel):
    platform: str
    url: str
    title: str


class ChatResponse(BaseModel):
    reply: str
    chart_data: Optional[ChartData] = None
    sources: list[Source] = []
    session_id: Optional[str] = None


class TopicQuerySchema(BaseModel):
    """Schema for Agent tool: search_topic_hotness."""
    topic: str
    platforms: Optional[str] = None  # comma-separated
    days: int = 7


class TriggerCollectSchema(BaseModel):
    """Schema for Agent tool: trigger_collection."""
    topic: str
    platforms: Optional[str] = None


class TopTopicsSchema(BaseModel):
    """Schema for Agent tool: get_top_topics."""
    platform: str
    limit: int = 10
