"""Collector supervisor — orchestrates multi-platform data collection."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from collector.base import DataSource, RawPost
from collector.github import GitHubSource
from collector.bilibili import BilibiliSource
from collector.xiaohongshu import XiaohongshuSource
from collector.zhihu import ZhihuSource
from collector.keywords import get_all_keywords, filter_tech_posts
from config import settings
from repository.posts import PostRepository

logger = logging.getLogger(__name__)


class CollectorSupervisor:
    """Orchestrates data collection across all platforms.

    Responsibilities:
    - Schedule collection tasks
    - Rate-limit requests per platform
    - Deduplicate results
    - Filter non-tech content
    """

    def __init__(self, post_repo: PostRepository):
        self.post_repo = post_repo
        self.sources: dict[str, DataSource] = {
            "github": GitHubSource(token=getattr(settings, "GITHUB_TOKEN", "")),
            "bilibili": BilibiliSource(),
            "xiaohongshu": XiaohongshuSource(),
            "zhihu": ZhihuSource(),
        }
        self._rate_limiters: dict[str, datetime] = {}
        self._min_interval: float = 5.0  # seconds between requests per platform

    async def collect_keyword(self, keyword: str, platforms: list[str] | None = None) -> dict[str, int]:
        """Collect posts for a single keyword across specified platforms.

        Returns: {platform: post_count}
        """
        targets = platforms or list(self.sources.keys())
        results = {}

        for platform in targets:
            source = self.sources.get(platform)
            if source is None:
                continue

            await self._rate_limit(platform)
            try:
                posts = await source.search(keyword, limit=50)
                posts = filter_tech_posts([p.to_dict() for p in posts])
                added = await self.post_repo.upsert_posts(posts)
                results[platform] = added
                logger.info(f"Collected {added} new posts for '{keyword}' from {platform}")
            except Exception as e:
                logger.error(f"Collection failed for '{keyword}' on {platform}: {e}")
                results[platform] = 0

        return results

    async def collect_all_keywords(self, platforms: list[str] | None = None) -> dict[str, int]:
        """Run a full collection round for all tech keywords.

        Returns: {platform: total_new_posts}
        """
        keywords = get_all_keywords()
        totals: dict[str, int] = {}

        for kw in keywords:
            result = await self.collect_keyword(kw, platforms)
            for plat, count in result.items():
                totals[plat] = totals.get(plat, 0) + count

        logger.info(f"Full collection round complete. Totals: {totals}")
        return totals

    async def collect_trending(self, platforms: list[str] | None = None) -> dict[str, int]:
        """Collect trending content from each platform.

        Returns: {platform: post_count}
        """
        targets = platforms or list(self.sources.keys())
        results = {}

        for platform in targets:
            source = self.sources.get(platform)
            if source is None:
                continue

            await self._rate_limit(platform)
            try:
                posts = await source.fetch_trending(limit=50)
                posts = filter_tech_posts([p.to_dict() for p in posts])
                added = await self.post_repo.upsert_posts(posts)
                results[platform] = added
                logger.info(f"Collected {added} trending posts from {platform}")
            except Exception as e:
                logger.error(f"Trending collection failed for {platform}: {e}")
                results[platform] = 0

        return results

    async def check_health(self) -> dict[str, bool]:
        """Check health of all data sources."""
        results = {}
        for name, source in self.sources.items():
            try:
                results[name] = await source.health_check()
            except Exception:
                results[name] = False
        return results

    async def _rate_limit(self, platform: str):
        """Enforce minimum interval between requests per platform."""
        now = datetime.utcnow()
        last = self._rate_limiters.get(platform)
        if last is not None:
            elapsed = (now - last).total_seconds()
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
        self._rate_limiters[platform] = datetime.utcnow()

    async def close(self):
        """Clean up resources."""
        for source in self.sources.values():
            if hasattr(source, 'close'):
                await source.close()
