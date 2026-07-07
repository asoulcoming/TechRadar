"""Bilibili data source — wraps MediaCrawler."""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from collector.base import DataSource, RawPost
from config import settings

logger = logging.getLogger(__name__)

# MediaCrawler CLI base command
MEDIACRAWLER_CMD = ["python", "main.py"]


class BilibiliSource(DataSource):
    platform = "bilibili"

    def __init__(self, media_crawler_path: Optional[str] = None):
        self.crawler_path = Path(media_crawler_path or settings.MEDIACRAWLER_PATH)
        self.available = self.crawler_path.exists()
        if not self.available:
            logger.warning(
                f"MediaCrawler not found at {self.crawler_path}. "
                "Bilibili source will use mock mode."
            )

    async def search(self, keyword: str, limit: int = 50) -> list[RawPost]:
        """Search B站 videos by keyword.

        Uses MediaCrawler to perform the search. Falls back to mock data
        when MediaCrawler is not installed.
        """
        if not self.available:
            return self._mock_search(keyword, limit)

        try:
            return await self._run_mediacrawler_search(keyword, limit)
        except Exception as e:
            logger.error(f"MediaCrawler B站 search failed: {e}")
            return self._mock_search(keyword, limit)

    async def fetch_trending(self, topic: str = "", limit: int = 50) -> list[RawPost]:
        """Fetch trending B站 videos."""
        if not self.available:
            return self._mock_trending(topic, limit)

        try:
            return await self._run_mediacrawler_search(topic or "编程", limit)
        except Exception as e:
            logger.error(f"MediaCrawler B站 trending failed: {e}")
            return self._mock_trending(topic, limit)

    async def health_check(self) -> bool:
        """Check if B站 source is operational."""
        if not self.available:
            return False
        try:
            proc = await asyncio.create_subprocess_exec(
                *MEDIACRAWLER_CMD, "--help",
                cwd=str(self.crawler_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except Exception:
            return False

    async def _run_mediacrawler_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Execute MediaCrawler CLI for B站 search.

        Example MediaCrawler command:
            python main.py --platform bilibili --lt qrcode --type search --keywords "Python"
        """
        output_file = self.crawler_path / "data" / "bilibili" / f"search_{keyword}.json"

        proc = await asyncio.create_subprocess_exec(
            *MEDIACRAWLER_CMD,
            "--platform", "bilibili",
            "--lt", "qrcode",
            "--type", "search",
            "--keywords", keyword,
            cwd=str(self.crawler_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=120
        )

        if proc.returncode != 0:
            logger.error(f"MediaCrawler exited with {proc.returncode}: {stderr.decode()[:500]}")
            return []

        # MediaCrawler writes results to CSV/JSON in data directory.
        # Try reading the output file.
        posts = []
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data[:limit]:
                    posts.append(self._parse_mediacrawler_item(keyword, item))
        return posts

    def _parse_mediacrawler_item(self, keyword: str, item: dict) -> RawPost:
        """Parse a MediaCrawler B站 result into a RawPost."""
        return RawPost(
            platform="bilibili",
            post_id=str(item.get("bvid", item.get("video_id", ""))),
            keyword=keyword,
            title=item.get("title", ""),
            url=f"https://www.bilibili.com/video/{item.get('bvid', '')}",
            author=item.get("owner_name", item.get("author", "")),
            view_count=int(item.get("view_count", item.get("video_play_count", 0))),
            like_count=int(item.get("like_count", item.get("liked_count", 0))),
            comment_count=int(item.get("comment_count", 0)),
            share_count=int(item.get("share_count", 0)),
            content_summary=item.get("desc", item.get("description", ""))[:200],
            tags=item.get("tags", []),
            raw_data=item,
        )

    def _mock_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Generate mock B站 data for development/testing."""
        logger.info(f"Using mock B站 data for keyword: {keyword}")
        posts = []
        for i in range(min(limit, 5)):
            posts.append(RawPost(
                platform="bilibili",
                post_id=f"mock-bv-{keyword}-{i}",
                keyword=keyword,
                title=f"[Mock] {keyword} 入门教程 - 第{i+1}期",
                url=f"https://www.bilibili.com/video/mock-{i}",
                author=f"UP主_{i}",
                view_count=10000 - i * 1000,
                like_count=500 - i * 80,
                comment_count=80 - i * 10,
                share_count=20 - i * 3,
                content_summary=f"这是一期关于 {keyword} 的技术教程视频。",
                tags=[keyword, "技术", "编程"],
                raw_data={"mock": True},
            ))
        return posts

    def _mock_trending(self, topic: str, limit: int) -> list[RawPost]:
        """Generate mock trending B站 data."""
        if topic:
            return self._mock_search(topic, limit)
        posts = []
        for kw in ["Python", "Go", "Rust", "AI", "前端"]:
            posts.extend(self._mock_search(kw, min(limit // 5, 3)))
        return posts[:limit]
