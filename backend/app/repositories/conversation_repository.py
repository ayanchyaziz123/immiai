from sqlalchemy import delete as _sql_delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from ..models.conversation import Conversation, Message, Role

# Pre-built loader options — created once at import, reused per-request
_WITH_MESSAGES    = selectinload(Conversation.messages)   # full load for /conversations/:id
_WITHOUT_MESSAGES = noload(Conversation.messages)         # metadata-only (list view, get_or_create)


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        """Fetch conversation with all messages (for display)."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(_WITH_MESSAGES)
        )
        return result.scalar_one_or_none()

    async def _get_head(self, conversation_id: str) -> Conversation | None:
        """Fetch conversation row only — messages not loaded."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(_WITHOUT_MESSAGES)
        )
        return result.scalar_one_or_none()

    async def create(self, title: str, user_id: str | None = None) -> Conversation:
        conversation = Conversation(title=title, user_id=user_id)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_or_create(
        self, conversation_id: str | None, title: str, user_id: str | None = None
    ) -> Conversation:
        if conversation_id:
            existing = await self._get_head(conversation_id)  # no message load needed
            if existing:
                return existing
        return await self.create(title, user_id=user_id)

    async def add_message(
        self, conversation_id: str, role: Role, content: str
    ) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        return message

    async def list_recent(
        self, user_id: str | None = None, limit: int = 20
    ) -> list[Conversation]:
        q = (
            select(Conversation)
            .options(_WITHOUT_MESSAGES)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        q = q.where(
            Conversation.user_id == user_id
            if user_id
            else Conversation.user_id.is_(None)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages without loading ORM objects."""
        exists = await self.db.scalar(
            select(Conversation.id).where(Conversation.id == conversation_id)
        )
        if exists is None:
            return False
        await self.db.execute(
            _sql_delete(Message).where(Message.conversation_id == conversation_id)
        )
        await self.db.execute(
            _sql_delete(Conversation).where(Conversation.id == conversation_id)
        )
        return True
