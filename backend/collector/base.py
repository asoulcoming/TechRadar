"""Abstract base class for all data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawPost:
    """Standardized post structure from any platform."""
    platform: str
    post_id: str
    keyword: str
    title: str = ""
    url: str = ""
    author: str = ""
    publish_time: Optional[datetime] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    star_count: int = 0
    content_summary: str = ""
    tags: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "post_id": self.post_id,
            "keyword": self.keyword,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "publish_time": self.publish_time,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "star_count": self.star_count,
            "content_summary": self.content_summary,
            "tags": self.tags,
            "raw_data": self.raw_data,
        }


class DataSource(ABC):
    """Abstract interface for platform-specific data collectors.

    Each platform (B站, 小红书, 知乎, GitHub) implements this interface.
    """

    platform: str  # "bilibili" | "xiaohongshu" | "zhihu" | "github"

    @abstractmethod
    async def search(self, keyword: str, limit: int = 50) -> list[RawPost]:
        """Search posts by keyword on this platform."""

    @abstractmethod
    async def fetch_trending(self, topic: str = "", limit: int = 50) -> list[RawPost]:
        """Fetch trending/热门 content, optionally filtered by topic."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the data source is operational."""
