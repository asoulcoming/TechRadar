"""Zhihu (知乎) data source — wraps MediaCrawler."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from collector.base import DataSource, RawPost
from config import settings

logger = logging.getLogger(__name__)

# MediaCrawler uses "zhihu"
MEDIACRAWLER_PLATFORM = "zhihu"


class ZhihuSource(DataSource):
    platform = "zhihu"

    def __init__(self):
        self.crawler_path = Path(settings.MEDIACRAWLER_PATH)
        self.available = self.crawler_path.exists()
        if not self.available:
            logger.warning(
                f"MediaCrawler not found at {self.crawler_path}. "
                "Zhihu source will use mock mode."
            )

    async def search(self, keyword: str, limit: int = 50) -> list[RawPost]:
        """Search 知乎 questions/answers by keyword.

        Uses MediaCrawler's run_search.py adapter (Playwright Chromium).
        Falls back to mock data on failure.
        """
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
        """Check if 知乎 source is operational."""
        if not self.available:
            return False
        try:
            python_bin = str(self.crawler_path / ".venv" / "bin" / "python")
            proc = await asyncio.create_subprocess_exec(
                python_bin, "run_search.py", "--help",
                cwd=str(self.crawler_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except Exception:
            return False

    async def _run_crawler_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Execute MediaCrawler via run_search.py adapter (Playwright mode).

        Uses Playwright's built-in Chromium — no system Chrome needed.
        Output: data/zhihu/search_contents_{date}.jsonl
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        output_file = (
            self.crawler_path / "data" / "zhihu" / f"search_contents_{today_str}.jsonl"
        )

        python_bin = str(self.crawler_path / ".venv" / "bin" / "python")
        cmd = [
            python_bin, "run_search.py",
            "--platform", MEDIACRAWLER_PLATFORM,
            "--keywords", keyword,
            "--type", "search",
            "--crawler_max_notes_count", str(limit),
        ]

        logger.info(f"Running MediaCrawler: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.crawler_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            stderr_str = stderr.decode("utf-8", errors="replace")[:1000]
            logger.error(f"MediaCrawler exited with {proc.returncode}: {stderr_str}")
            raise RuntimeError(f"MediaCrawler exited with code {proc.returncode}")

        posts = []
        if output_file.exists():
            with open(output_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                        posts.append(self._parse_mediacrawler_item(keyword, item))
                    except json.JSONDecodeError:
                        continue
        else:
            raise FileNotFoundError(f"MediaCrawler output file not found: {output_file}")

        if not posts:
            logger.warning(f"MediaCrawler returned 0 posts for '{keyword}'")
        return posts[:limit]

    def _parse_mediacrawler_item(self, keyword: str, item: dict) -> RawPost:
        """Parse a MediaCrawler 知乎 result into a RawPost."""
        question_id = str(item.get("question_id", item.get("id", "")))
        return RawPost(
            platform="zhihu",
            post_id=question_id,
            keyword=keyword,
            title=item.get("title", item.get("question_title", "")),
            url=item.get("question_url",
                         f"https://www.zhihu.com/question/{question_id}"),
            author=(item.get("nickname", item.get("author_name", item.get("author", {}).get("name", ""))) or ""),
            view_count=int(item.get("view_count", item.get("visit_count", 0))),
            like_count=int(item.get("like_count", item.get("voteup_count", 0))),
            comment_count=int(item.get("comment_count", 0)),
            share_count=int(item.get("share_count", 0)),
            content_summary=(item.get("excerpt", item.get("content", "")) or "")[:200],
            tags=item.get("topics", item.get("tags", [])),
            raw_data=item,
        )

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
