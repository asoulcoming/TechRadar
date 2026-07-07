"""DailyReport repository."""

from datetime import date
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from repository.models import DailyReport


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_report(self, report: dict) -> DailyReport:
        r = DailyReport(**report)
        self.db.add(r)
        await self.db.commit()
        await self.db.refresh(r)
        return r

    async def get_latest(self) -> Optional[DailyReport]:
        stmt = select(DailyReport).order_by(desc(DailyReport.report_date)).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_date_range(self, start: date, end: date) -> list[DailyReport]:
        stmt = (
            select(DailyReport)
            .where(DailyReport.report_date >= start, DailyReport.report_date <= end)
            .order_by(desc(DailyReport.report_date))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def exists_for_date(self, report_date: date) -> bool:
        stmt = select(DailyReport).where(DailyReport.report_date == report_date)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
