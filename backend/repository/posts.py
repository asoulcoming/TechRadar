"""RawPost repository."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from repository.models import RawPost


class PostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_posts(self, posts: list[dict]) -> int:
        """Insert or update posts. Returns count of newly inserted."""
        added = 0
        for p in posts:
            existing = await self.db.execute(
                select(RawPost).where(
                    and_(
                        RawPost.platform == p["platform"],
                        RawPost.post_id == p["post_id"],
                    )
                )
            )
            existing = existing.scalar_one_or_none()
            if existing:
                # Update metrics
                for key in ("view_count", "like_count", "comment_count", "share_count", "star_count"):
                    if key in p:
                        setattr(existing, key, p[key])
                existing.fetched_at = datetime.utcnow()
            else:
                post = RawPost(**p)
                self.db.add(post)
                added += 1
        await self.db.commit()
        return added

    async def query(
        self,
        topic: Optional[str] = None,
        platform: Optional[str] = None,
        days: int = 7,
        limit: int = 50,
    ) -> list[RawPost]:
        """Query posts with optional filters."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = select(RawPost).where(RawPost.fetched_at >= cutoff)

        if platform:
            stmt = stmt.where(RawPost.platform == platform)
        if topic:
            stmt = stmt.where(
                RawPost.keyword.like(f"%{topic}%")
                | RawPost.title.like(f"%{topic}%")
                | RawPost.tags.contains(topic)
            )

        stmt = stmt.order_by(RawPost.fetched_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_top_posts(
        self, topic: str, platform: Optional[str] = None, limit: int = 5
    ) -> list[RawPost]:
        """Get top posts for a topic, sorted by engagement."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        stmt = select(RawPost).where(
            RawPost.fetched_at >= cutoff,
            RawPost.keyword.like(f"%{topic}%") | RawPost.title.like(f"%{topic}%"),
        )
        if platform:
            stmt = stmt.where(RawPost.platform == platform)

        stmt = stmt.order_by(
            (RawPost.like_count + RawPost.comment_count * 2 + RawPost.share_count * 3).desc()
        ).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_platform(self, days: int = 1) -> dict[str, int]:
        """Count posts per platform in recent days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(RawPost.platform, func.count(RawPost.id))
            .where(RawPost.fetched_at >= cutoff)
            .group_by(RawPost.platform)
        )
        result = await self.db.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
