"""Import MediaCrawler JSONL output into the TechRadar database.

Reads JSONL files from MediaCrawler's data/ directory structure,
parses each record using the platform-specific collector logic,
and upserts them into the raw_posts table.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from repository.posts import PostRepository
from collector.bilibili import BilibiliSource
from collector.xiaohongshu import XiaohongshuSource
from collector.zhihu import ZhihuSource
from collector.keywords import filter_tech_posts
from config import settings

logger = logging.getLogger(__name__)

# Platform → (collector instance, MediaCrawler platform dir name)
_PLATFORM_CONFIG = {
    "bilibili": ("bili", BilibiliSource()),
    "xiaohongshu": ("xhs", XiaohongshuSource()),
    "zhihu": ("zhihu", ZhihuSource()),
}

# GitHub doesn't use MediaCrawler — skip for now; it writes via API directly


async def import_from_mediacrawler(
    post_repo: PostRepository,
    platforms: list[str] | None = None,
    target_date: str | None = None,
) -> dict[str, int]:
    """Read MediaCrawler JSONL files and import into raw_posts.

    Args:
        post_repo: PostRepository instance for database writes.
        platforms: Platforms to import (default: all three Chinese platforms).
        target_date: Date string YYYY-MM-DD (default: today).

    Returns:
        {platform: count_of_new_posts}
    """
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    crawler_root = Path(settings.MEDIACRAWLER_PATH)
    targets = platforms or list(_PLATFORM_CONFIG.keys())
    totals: dict[str, int] = {}

    for platform in targets:
        config = _PLATFORM_CONFIG.get(platform)
        if config is None:
            logger.warning(f"No importer config for platform: {platform}")
            continue

        crawler_dir, source = config
        jsonl_dir = crawler_root / "data" / crawler_dir / "jsonl"

        # Try target_date first, fall back to latest available file
        content_file = _find_latest_jsonl(jsonl_dir, "search_contents", target_date)
        comment_file = _find_latest_jsonl(jsonl_dir, "search_comments", target_date)

        posts = _read_jsonl(content_file, platform)
        # Also read comments if available (comments enrich content)
        comments = _read_jsonl(comment_file, platform)

        if not posts:
            logger.warning(f"No content found in {content_file}")
            continue

        # Parse each record into our standardized RawPost dict
        raw_posts = []
        for item in posts:
            try:
                post = source._parse_mediacrawler_item(
                    item.get("source_keyword", ""), item
                )
                raw_posts.append(post.to_dict())
            except Exception as e:
                logger.warning(f"Failed to parse {platform} post {item.get('id', '?')}: {e}")

        # Filter non-tech content
        raw_posts = filter_tech_posts(raw_posts)

        # Upsert into database
        added = await post_repo.upsert_posts(raw_posts)
        totals[platform] = added
        logger.info(
            f"Imported {len(raw_posts)} posts ({added} new) from {platform} "
            f"[{target_date}]  + {len(comments)} comments skipped"
        )

    return totals


def _read_jsonl(filepath: Path, platform: str) -> list[dict]:
    """Read a JSONL file, returning list of dicts."""
    if not filepath.exists():
        return []
    items = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Bad JSONL line in {filepath}: {e}")
    return items


def _find_latest_jsonl(directory: Path, prefix: str, target_date: str) -> Path:
    """Find the latest JSONL file matching the prefix, preferring target_date.

    Falls back to the most recent file if the exact date isn't available.
    """
    if not directory.exists():
        return directory / f"{prefix}_{target_date}.jsonl"  # will fail gracefully

    # Exact match first
    exact = directory / f"{prefix}_{target_date}.jsonl"
    if exact.exists():
        return exact

    # Fall back to most recent matching file
    candidates = sorted(
        directory.glob(f"{prefix}_*.jsonl"),
        key=lambda p: p.name,
        reverse=True,
    )
    if candidates:
        logger.info(f"No data for {target_date}, using {candidates[0].name}")
        return candidates[0]

    return exact  # no candidates at all
