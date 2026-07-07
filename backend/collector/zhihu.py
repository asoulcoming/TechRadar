"""Zhihu (知乎) data source — wraps MediaCrawler."""

import asyncio
import json
import logging
from pathlib import Path

from collector.base import DataSource, RawPost
from config import settings

logger = logging.getLogger(__name__)


class ZhihuSource(DataSource):
    platform = "zhihu"

    def __init__(self):
        self.crawler_path = Path(settings.MEDIACRAWLER_PATH)
        self.available = self.crawler_path.exists()

    async def search(self, keyword: str, limit: int = 50) -> list[RawPost]:
        """Search 知乎 questions/answers by keyword."""
        if not self.available:
            return self._mock_search(keyword, limit)

        try:
            return await self._run_crawler_search(keyword, limit)
        except Exception as e:
            logger.error(f"MediaCrawler 知乎 search failed: {e}")
            return self._mock_search(keyword, limit)

    async def fetch_trending(self, topic: str = "", limit: int = 50) -> list[RawPost]:
        """Fetch trending 知乎 content."""
        if not self.available:
            return self._mock_search(topic or "编程", limit)

        try:
            return await self._run_crawler_search(topic or "技术", limit)
        except Exception as e:
            logger.error(f"MediaCrawler 知乎 trending failed: {e}")
            return self._mock_search(topic or "编程", limit)

    async def health_check(self) -> bool:
        return self.available

    async def _run_crawler_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Execute MediaCrawler for 知乎."""
        output_file = self.crawler_path / "data" / "zhihu" / f"search_{keyword}.json"
        proc = await asyncio.create_subprocess_exec(
            "python", "main.py",
            "--platform", "zhihu",
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
                        platform="zhihu",
                        post_id=str(item.get("question_id", item.get("id", ""))),
                        keyword=keyword,
                        title=item.get("title", item.get("question_title", "")),
                        url=f"https://www.zhihu.com/question/{item.get('question_id', '')}",
                        author=item.get("author", {}).get("name", ""),
                        view_count=item.get("view_count", item.get("visit_count", 0)),
                        like_count=item.get("like_count", item.get("voteup_count", 0)),
                        comment_count=item.get("comment_count", 0),
                        share_count=0,
                        content_summary=item.get("excerpt", item.get("content", ""))[:200],
                        tags=item.get("topics", item.get("tags", [])),
                        raw_data=item,
                    ))
        return posts

    def _mock_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Generate mock 知乎 data."""
        posts = []
        questions = [
            f"{keyword} 在 2026 年的发展前景如何？",
            f"如何高效学习 {keyword}？分享学习路线",
            f"为什么 {keyword} 越来越流行？技术深度分析",
        ]
        for i in range(min(limit, len(questions))):
            posts.append(RawPost(
                platform="zhihu",
                post_id=f"mock-zh-{keyword}-{i}",
                keyword=keyword,
                title=questions[i],
                url=f"https://www.zhihu.com/question/mock-{i}",
                author=f"技术大牛_{i}",
                view_count=50000 - i * 8000,
                like_count=1200 - i * 200,
                comment_count=150 - i * 20,
                content_summary=f"关于 {keyword} 的几个关键观点和分析。",
                tags=[keyword, "技术", "编程", "职业发展"],
                raw_data={"mock": True},
            ))
        return posts
