"""Bilibili data source — wraps MediaCrawler."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from collector.base import DataSource, RawPost
from config import settings

logger = logging.getLogger(__name__)

# MediaCrawler uses "bili" for B站
MEDIACRAWLER_PLATFORM = "bili"


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

        Uses MediaCrawler's run_search.py adapter (Playwright Chromium, no system Chrome needed).
        Falls back to mock data on failure.
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
        """Check if B站 source is operational (Playwright Chromium mode)."""
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

    async def _run_mediacrawler_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Execute MediaCrawler via run_search.py adapter (Playwright mode).

        Uses Playwright's built-in Chromium — no system Chrome needed.
        Output: data/bili/search_contents_{date}.jsonl
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        output_file = (
            self.crawler_path / "data" / "bili" / f"search_contents_{today_str}.jsonl"
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
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=300
        )

        if proc.returncode != 0:
            stderr_str = stderr.decode("utf-8", errors="replace")[:1000]
            logger.error(f"MediaCrawler exited with {proc.returncode}: {stderr_str}")
            raise RuntimeError(f"MediaCrawler exited with code {proc.returncode}")

        # MediaCrawler writes results as JSONL (one JSON object per line)
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
        """Parse a MediaCrawler B站 result into a RawPost."""
        # MediaCrawler B站 fields: video_id, title, video_url, author_name,
        # view_count, like_count, comment_count, share_count, description, tags
        video_id = str(item.get("video_id", item.get("bvid", "")))
        return RawPost(
            platform="bilibili",
            post_id=video_id,
            keyword=keyword,
            title=item.get("title", ""),
            url=item.get("video_url", f"https://www.bilibili.com/video/{video_id}"),
            author=item.get("nickname", item.get("author_name", item.get("author", ""))),
            publish_time=_parse_timestamp(item.get("create_time")),
            view_count=int(item.get("view_count", item.get("video_play_count", 0))),
            like_count=int(item.get("like_count", item.get("liked_count", 0))),
            comment_count=int(item.get("comment_count", 0)),
            share_count=int(item.get("share_count", 0)),
            content_summary=(item.get("description", item.get("desc", "")) or "")[:200],
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


def _parse_timestamp(value) -> Optional[datetime]:
    """Parse various timestamp formats from MediaCrawler."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        if value > 1_000_000_000_000:  # milliseconds
            value = value / 1000
        try:
            return datetime.fromtimestamp(value)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None
