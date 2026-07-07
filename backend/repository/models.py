"""SQLAlchemy ORM models (table definitions)."""

import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, DateTime, Text, JSON, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class RawPost(Base):
    __tablename__ = "raw_posts"
    __table_args__ = (
        UniqueConstraint("platform", "post_id", "fetched_at", name="uq_platform_post_fetched"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    post_id: Mapped[str] = mapped_column(String(128), nullable=False)
    keyword: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), default="")
    url: Mapped[str] = mapped_column(String(1024), default="")
    author: Mapped[str] = mapped_column(String(128), default="")
    publish_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    star_count: Mapped[int] = mapped_column(Integer, default=0)
    content_summary: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(JSON, default=list)
    raw_data: Mapped[str] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyHotness(Base):
    __tablename__ = "daily_hotness"
    __table_args__ = (
        UniqueConstraint("topic", "platform", "date", name="uq_topic_platform_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    hotness_score: Mapped[float] = mapped_column(Float, default=0.0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_likes: Mapped[int] = mapped_column(Integer, default=0)
    total_comments: Mapped[int] = mapped_column(Integer, default=0)
    top_posts: Mapped[str] = mapped_column(JSON, default=list)


class MonitoredTopic(Base):
    __tablename__ = "monitored_topics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    keywords: Mapped[str] = mapped_column(String(512), nullable=False)
    platforms: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_date: Mapped[Date] = mapped_column(Date, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    top_topics: Mapped[str] = mapped_column(JSON, default=list)
    platform_highlights: Mapped[str] = mapped_column(JSON, default=list)
    rising_topics: Mapped[str] = mapped_column(JSON, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeishuConfig(Base):
    __tablename__ = "feishu_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    webhook_url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str] = mapped_column(String(256), default="")
    push_daily_report: Mapped[bool] = mapped_column(Boolean, default=True)
    push_breaking: Mapped[bool] = mapped_column(Boolean, default=True)
    breaking_threshold: Mapped[float] = mapped_column(Float, default=30.0)
    push_time: Mapped[str] = mapped_column(String(8), default="09:00")  # HH:MM format
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    platforms: Mapped[str] = mapped_column(String(256), nullable=False)
    frequency: Mapped[str] = mapped_column(String(16), default="daily")
    push_channel: Mapped[str] = mapped_column(String(32), default="feishu")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
