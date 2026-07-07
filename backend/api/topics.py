"""Topic monitoring endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from repository.topics import TopicRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topics", tags=["topics"])


class TopicCreate(BaseModel):
    topic: str
    keywords: str
    platforms: str


class TopicOut(BaseModel):
    id: int
    topic: str
    keywords: str
    platforms: str
    active: bool

    class Config:
        from_attributes = True


@router.get("/monitor", response_model=list[TopicOut])
async def list_monitored_topics(db: AsyncSession = Depends(get_db)):
    """List all actively monitored topics."""
    repo = TopicRepository(db)
    topics = await repo.list_active()
    return topics


@router.post("/monitor", response_model=TopicOut)
async def add_monitored_topic(body: TopicCreate, db: AsyncSession = Depends(get_db)):
    """Add a new topic to monitor."""
    repo = TopicRepository(db)
    topic = await repo.add(
        topic=body.topic,
        keywords=body.keywords,
        platforms=body.platforms,
    )
    return topic


@router.delete("/monitor/{topic_id}")
async def remove_monitored_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    """Deactivate a monitored topic."""
    repo = TopicRepository(db)
    await repo.deactivate(topic_id)
    return {"status": "ok"}
