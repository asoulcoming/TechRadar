"""AlertSubscription repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from repository.models import AlertSubscription


class SubscriptionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_active(self) -> list[AlertSubscription]:
        stmt = select(AlertSubscription).where(AlertSubscription.active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def add(self, topic: str, platforms: str, frequency: str = "daily",
                  push_channel: str = "feishu") -> AlertSubscription:
        sub = AlertSubscription(
            topic=topic, platforms=platforms,
            frequency=frequency, push_channel=push_channel,
        )
        self.db.add(sub)
        await self.db.commit()
        await self.db.refresh(sub)
        return sub

    async def deactivate(self, sub_id: int) -> None:
        sub = await self.db.get(AlertSubscription, sub_id)
        if sub:
            sub.active = False
            await self.db.commit()
