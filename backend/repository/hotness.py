"""DailyHotness repository."""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from repository.models import DailyHotness


class HotnessRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_snapshot(self, snapshots: list[dict]) -> None:
        """Save daily hotness snapshots (upsert by topic+platform+date)."""
        for s in snapshots:
            existing = await self.db.execute(
                select(DailyHotness).where(
                    and_(
                        DailyHotness.topic == s["topic"],
                        DailyHotness.platform == s["platform"],
                        DailyHotness.date == s["date"],
                    )
                )
            )
            existing = existing.scalar_one_or_none()
            if existing:
                for key, val in s.items():
                    if key != "id":
                        setattr(existing, key, val)
            else:
                self.db.add(DailyHotness(**s))
        await self.db.commit()

    async def get_trend(
        self, topic: str, platform: Optional[str] = None, days: int = 30
    ) -> list[DailyHotness]:
        """Get trend data for a topic."""
        cutoff = date.today() - timedelta(days=days)
        stmt = select(DailyHotness).where(
            DailyHotness.topic == topic,
            DailyHotness.date >= cutoff,
        )
        if platform:
            stmt = stmt.where(DailyHotness.platform == platform)

        stmt = stmt.order_by(DailyHotness.date.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_ranking(
        self,
        target_date: Optional[date] = None,
        platform: Optional[str] = None,
        limit: int = 20,
    ) -> list[DailyHotness]:
        """Get top topics by hotness score for a given date."""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)  # default: yesterday

        stmt = select(DailyHotness).where(DailyHotness.date == target_date)
        if platform:
            stmt = stmt.where(DailyHotness.platform == platform)

        stmt = stmt.order_by(DailyHotness.hotness_score.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_top_topics(
        self, days: int = 1, limit: int = 20, platform: str | None = None
    ) -> list[dict]:
        """Get top topics aggregated across recent days, optionally by platform."""
        cutoff = date.today() - timedelta(days=days)
        stmt = (
            select(
                DailyHotness.topic,
                func.avg(DailyHotness.hotness_score).label("avg_score"),
                func.sum(DailyHotness.post_count).label("total_posts"),
            )
            .where(DailyHotness.date >= cutoff)
        )
        if platform:
            stmt = stmt.where(DailyHotness.platform == platform)
        stmt = stmt.group_by(DailyHotness.topic).order_by(desc("avg_score")).limit(limit)
        result = await self.db.execute(stmt)
        return [
            {"topic": row[0], "avg_score": round(row[1], 1), "total_posts": row[2]}
            for row in result.all()
        ]
