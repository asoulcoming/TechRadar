"""End-to-end data pipeline: import → normalize → hotness snapshot.

Orchestrates the full data flow from raw MediaCrawler output
to structured daily hotness snapshots ready for the dashboard.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from collector.importer import import_from_mediacrawler
from repository.posts import PostRepository
from repository.hotness import HotnessRepository
from analyzer.normalizer import compute_daily_hotness

logger = logging.getLogger(__name__)


async def run_data_pipeline(
    post_repo: PostRepository,
    hotness_repo: HotnessRepository,
    target_date: date | None = None,
    platforms: list[str] | None = None,
) -> dict:
    """Run the full data pipeline for a given date.

    1. Import MediaCrawler JSONL → raw_posts table
    2. For each keyword+platform combo, compute daily hotness scores
    3. Save snapshots to daily_hotness table

    Args:
        post_repo: PostRepository for raw_posts access.
        hotness_repo: HotnessRepository for hotness snapshots.
        target_date: Date to process (default: today).
        platforms: Platforms to process (default: all).

    Returns:
        Summary dict with import counts and snapshot count.
    """
    if target_date is None:
        target_date = date.today()

    date_str = target_date.isoformat()

    # ── Step 1: Import from MediaCrawler ──
    logger.info(f"[Pipeline] Step 1: Importing MediaCrawler data for {date_str}...")
    import_counts = await import_from_mediacrawler(
        post_repo=post_repo,
        platforms=platforms,
        target_date=date_str,
    )
    total_imported = sum(import_counts.values())
    logger.info(f"[Pipeline] Import complete: {import_counts}")

    # ── Step 2: Compute hotness for each keyword × platform ──
    logger.info(f"[Pipeline] Step 2: Computing hotness scores...")
    from collector.keywords import get_all_keywords

    keywords = get_all_keywords()
    target_platforms = platforms or list(import_counts.keys())
    snapshots = []

    for keyword in keywords:
        for platform in target_platforms:
            # Get recent posts for this keyword+platform combo
            posts = await post_repo.query(
                topic=keyword,
                platform=platform,
                days=3,  # last 3 days for context
                limit=500,
            )

            if not posts:
                continue

            # Convert ORM objects to dicts for the normalizer
            post_dicts = [_post_to_dict(p) for p in posts]

            # Compute daily hotness
            snapshot = compute_daily_hotness(
                posts=post_dicts,
                topic=keyword,
                platform=platform,
                target_date=target_date,
            )

            if snapshot["hotness_score"] > 0 or snapshot["post_count"] > 0:
                snapshots.append(snapshot)

    # ── Step 3: Save hotness snapshots ──
    if snapshots:
        await hotness_repo.save_snapshot(snapshots)
        logger.info(f"[Pipeline] Saved {len(snapshots)} hotness snapshots")
    else:
        logger.warning("[Pipeline] No snapshots generated — no posts found for today")

    return {
        "date": date_str,
        "imported_posts": total_imported,
        "snapshots": len(snapshots),
        "by_platform": import_counts,
    }


def _post_to_dict(post) -> dict:
    """Convert a RawPost ORM object to a plain dict for the normalizer."""
    return {
        "platform": post.platform,
        "post_id": post.post_id,
        "keyword": post.keyword,
        "title": post.title,
        "url": post.url,
        "author": post.author,
        "publish_time": post.publish_time,
        "view_count": post.view_count,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "share_count": post.share_count,
        "star_count": post.star_count,
        "content_summary": post.content_summary,
        "tags": post.tags,
    }
