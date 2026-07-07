"""Hotness score normalization.

Converts raw platform metrics into a unified [0, 100] hotness score.
"""

import math
from datetime import date, timedelta

import numpy as np

from repository.posts import PostRepository


# Per-platform weight configs
PLATFORM_WEIGHTS = {
    "bilibili": {"views": 0.30, "likes": 0.25, "comments": 0.25, "shares": 0.20},
    "xiaohongshu": {"views": 0.20, "likes": 0.30, "comments": 0.30, "shares": 0.20},
    "zhihu": {"views": 0.30, "likes": 0.35, "comments": 0.35, "shares": 0.0},
    "github": {"views": 0.10, "likes": 0.50, "comments": 0.15, "shares": 0.25},  # likes=stars, shares=forks
}


def compute_post_hotness(post: dict, platform: str) -> float:
    """Compute normalized hotness score for a single post.

    Uses percentile-based normalization within platform metrics.
    Score range: [0, 100]
    """
    weights = PLATFORM_WEIGHTS.get(platform, {"views": 0.3, "likes": 0.3, "comments": 0.2, "shares": 0.2})

    # Get raw values, default 0
    views = post.get("view_count", 0) or 0
    likes = post.get("like_count", 0) or 0
    comments = post.get("comment_count", 0) or 0
    shares = post.get("share_count", 0) or 0

    # Log-transform to compress large ranges, then scale to 0-100
    def log_score(val: int, base: int = 10) -> float:
        if val <= 0:
            return 0
        return min(math.log(val + 1, base) * 20, 100)

    raw_score = (
        weights["views"] * log_score(views) +
        weights["likes"] * log_score(likes) +
        weights["comments"] * log_score(comments) +
        weights["shares"] * log_score(shares)
    )
    return min(raw_score, 100)


def compute_daily_hotness(
    posts: list[dict],
    topic: str,
    platform: str,
    target_date: date,
    decay_lambda: float = 0.05,
) -> dict:
    """Compute the daily hotness score for a topic on a platform.

    Applies time decay so older posts contribute less to the score.

    Args:
        posts: List of post dicts from the repo.
        topic: The topic name.
        platform: Platform identifier.
        target_date: The date to compute for.
        decay_lambda: Decay rate (higher = faster decay).

    Returns: Daily hotness snapshot dict.
    """
    if not posts:
        return {
            "topic": topic,
            "platform": platform,
            "date": target_date,
            "hotness_score": 0.0,
            "post_count": 0,
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "top_posts": [],
        }

    total_score = 0.0
    total_views = 0
    total_likes = 0
    total_comments = 0
    scored_posts = []

    for p in posts:
        post_score = compute_post_hotness(p, platform)

        # Time decay: hours since target_date
        pub_time = p.get("publish_time")
        if pub_time:
            hours_ago = max(0, (target_date - pub_time.date()).days * 24)
            decay = math.exp(-decay_lambda * hours_ago)
            post_score *= decay

        total_score += post_score
        total_views += p.get("view_count", 0) or 0
        total_likes += p.get("like_count", 0) or 0
        total_comments += p.get("comment_count", 0) or 0
        scored_posts.append((p.get("post_id", ""), post_score))

    # Get top 5 posts by score
    scored_posts.sort(key=lambda x: x[1], reverse=True)

    return {
        "topic": topic,
        "platform": platform,
        "date": target_date,
        "hotness_score": round(min(total_score, 100), 1),
        "post_count": len(posts),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "top_posts": [p[0] for p in scored_posts[:5]],
    }
