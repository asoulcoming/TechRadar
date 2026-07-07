"""Xiaohongshu (小红书) data source — wraps MediaCrawler."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from collector.base import DataSource, RawPost
from config import settings

logger = logging.getLogger(__name__)

# MediaCrawler uses "xhs" for 小红书
MEDIACRAWLER_PLATFORM = "xhs"


class XiaohongshuSource(DataSource):
    platform = "xiaohongshu"

    def __init__(self):
        self.crawler_path = Path(settings.MEDIACRAWLER_PATH)
        self.available = self.crawler_path.exists()
        if not self.available:
            logger.warning(
                f"MediaCrawler not found at {self.crawler_path}. "
                "Xiaohongshu source will use mock mode."
            )

    async def search(self, keyword: str, limit: int = 50) -> list[RawPost]:
        """Search 小红书 notes by keyword.

        Uses MediaCrawler's run_search.py adapter (Playwright Chromium).
        Falls back to mock data on failure.
        """
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
        """Check if 小红书 source is operational."""
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
        Output: data/xhs/search_contents_{date}.jsonl
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        output_file = (
            self.crawler_path / "data" / "xhs" / f"search_contents_{today_str}.jsonl"
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
        """Parse a MediaCrawler 小红书 result into a RawPost."""
        note_id = str(item.get("note_id", ""))
        return RawPost(
            platform="xiaohongshu",
            post_id=note_id,
            keyword=keyword,
            title=(item.get("title", item.get("desc", "")) or "")[:100],
            url=item.get("note_url",
                         f"https://www.xiaohongshu.com/explore/{note_id}"),
            author=(item.get("nickname", item.get("author_name", item.get("user", {}).get("nickname", ""))) or ""),
            view_count=int(item.get("view_count", 0)),
            like_count=int(item.get("like_count", item.get("liked_count", 0))),
            comment_count=int(item.get("comment_count", 0)),
            share_count=int(item.get("share_count", item.get("collected_count", 0))),
            content_summary=(item.get("desc", "") or "")[:200],
            tags=item.get("tags", item.get("tag_list", [])),
            raw_data=item,
        )

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
