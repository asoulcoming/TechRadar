"""MonitoredTopic repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repository.models import MonitoredTopic


class TopicRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active(self) -> list[MonitoredTopic]:
        stmt = select(MonitoredTopic).where(MonitoredTopic.active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add(self, topic: str, keywords: str, platforms: str) -> MonitoredTopic:
        t = MonitoredTopic(topic=topic, keywords=keywords, platforms=platforms)
        self.db.add(t)
        await self.db.commit()
        await self.db.refresh(t)
        return t

    async def deactivate(self, topic_id: int) -> None:
        t = await self.db.get(MonitoredTopic, topic_id)
        if t:
            t.active = False
            await self.db.commit()
