"""Xiaohongshu (小红书) data source — wraps MediaCrawler."""

import asyncio
import json
import logging
from pathlib import Path

from collector.base import DataSource, RawPost
from config import settings

logger = logging.getLogger(__name__)


class XiaohongshuSource(DataSource):
    platform = "xiaohongshu"

    def __init__(self):
        self.crawler_path = Path(settings.MEDIACRAWLER_PATH)
        self.available = self.crawler_path.exists()

    async def search(self, keyword: str, limit: int = 50) -> list[RawPost]:
        """Search 小红书 notes by keyword."""
        if not self.available:
            return self._mock_search(keyword, limit)

        try:
            return await self._run_crawler_search(keyword, limit)
        except Exception as e:
            logger.error(f"MediaCrawler 小红书 search failed: {e}")
            return self._mock_search(keyword, limit)

    async def fetch_trending(self, topic: str = "", limit: int = 50) -> list[RawPost]:
        """Fetch trending 小红书 notes."""
        if not self.available:
            return self._mock_search(topic or "编程", limit)

        try:
            return await self._run_crawler_search(topic or "技术", limit)
        except Exception as e:
            logger.error(f"MediaCrawler 小红书 trending failed: {e}")
            return self._mock_search(topic or "编程", limit)

    async def health_check(self) -> bool:
        return self.available

    async def _run_crawler_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Execute MediaCrawler for 小红书."""
        output_file = self.crawler_path / "data" / "xhs" / f"search_{keyword}.json"
        proc = await asyncio.create_subprocess_exec(
            "python", "main.py",
            "--platform", "xhs",
            "--lt", "qrcode",
            "--type", "search",
            "--keywords", keyword,
            cwd=str(self.crawler_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=120)

        posts = []
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data[:limit]:
                    posts.append(RawPost(
                        platform="xiaohongshu",
                        post_id=str(item.get("note_id", "")),
                        keyword=keyword,
                        title=item.get("title", item.get("desc", ""))[:100],
                        url=f"https://www.xiaohongshu.com/explore/{item.get('note_id', '')}",
                        author=item.get("user", {}).get("nickname", ""),
                        view_count=item.get("view_count", 0),
                        like_count=item.get("like_count", item.get("liked_count", 0)),
                        comment_count=item.get("comment_count", 0),
                        share_count=item.get("share_count", 0),
                        content_summary=item.get("desc", "")[:200],
                        tags=item.get("tags", item.get("tag_list", [])),
                        raw_data=item,
                    ))
        return posts

    def _mock_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Generate mock 小红书 data."""
        posts = []
        for i in range(min(limit, 5)):
            posts.append(RawPost(
                platform="xiaohongshu",
                post_id=f"mock-xhs-{keyword}-{i}",
                keyword=keyword,
                title=f"[Mock] 程序员必学的 {keyword} 技巧，效率翻倍！",
                url=f"https://www.xiaohongshu.com/explore/mock-{i}",
                author=f"技术博主_{i}",
                view_count=5000 - i * 500,
                like_count=300 - i * 50,
                comment_count=40 - i * 5,
                share_count=60 - i * 10,
                content_summary=f"推荐几个 {keyword} 相关的实用工具和学习资源。",
                tags=[keyword, "编程", "程序员日常", "效率工具"],
                raw_data={"mock": True},
            ))
        return posts
