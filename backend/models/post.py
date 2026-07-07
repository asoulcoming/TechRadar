"""Post-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PlatformMetrics(BaseModel):
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    stars: Optional[int] = None


class RawPostOut(BaseModel):
    platform: str
    post_id: str
    title: str
    url: str
    author: str
    publish_time: Optional[datetime] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    star_count: Optional[int] = None
    content_summary: str = ""
    tags: list[str] = []
    keyword: str = ""

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    posts: list[RawPostOut]
    total: int
    platform: str
    keyword: str
