"""Conversation memory management."""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from repository.models import ConversationHistory

MAX_HISTORY_PER_SESSION = 20
SESSION_TTL_HOURS = 24


class ConversationMemory:
    """Manages conversation history per session."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        msg = ConversationHistory(
            session_id=session_id,
            role=role,
            content=content,
        )
        self.db.add(msg)
        await self.db.commit()

    async def get_history(
        self, session_id: str, limit: int = MAX_HISTORY_PER_SESSION
    ) -> list[dict]:
        """Get recent conversation history for a session."""
        stmt = (
            select(ConversationHistory)
            .where(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())
        messages.reverse()  # chronological order
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]

    async def cleanup_old_sessions(self) -> int:
        """Delete conversations older than TTL. Returns count of deleted."""
        cutoff = datetime.utcnow() - timedelta(hours=SESSION_TTL_HOURS)
        stmt = delete(ConversationHistory).where(
            ConversationHistory.created_at < cutoff
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    @staticmethod
    def generate_session_id() -> str:
        return str(uuid.uuid4())[:8]
