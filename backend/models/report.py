"""Report-related Pydantic schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class DailyReportOut(BaseModel):
    id: int
    report_date: date
    title: str
    summary: str
    top_topics: list[dict] = []
    platform_highlights: list[dict] = []
    rising_topics: list[dict] = []
    generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    reports: list[DailyReportOut]
    total: int


class FeishuConfigRequest(BaseModel):
    webhook_url: str
    secret: Optional[str] = None
    push_daily_report: bool = True
    push_breaking: bool = True
    breaking_threshold: float = 30.0
    push_time: str = "09:00"


class SubscriptionRequest(BaseModel):
    topic: str
    platforms: str  # comma-separated
    frequency: str = "daily"
    push_channel: str = "feishu"
