from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from ..models.conversation import Conversation, Message, Role

_WITH_MESSAGES  = selectinload(Conversation.messages)
_WITHOUT_MESSAGES = noload(Conversation.messages)   # list view — metadata only


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(_WITH_MESSAGES)
        )
        return result.scalar_one_or_none()

    async def create(self, title: str, user_id: str | None = None) -> Conversation:
        conversation = Conversation(title=title, user_id=user_id)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_or_create(self, conversation_id: str | None, title: str, user_id: str | None = None) -> Conversation:
        if conversation_id:
            existing = await self.get_by_id(conversation_id)
            if existing:
                return existing
        return await self.create(title, user_id=user_id)

    async def add_message(
        self, conversation_id: str, role: Role, content: str
    ) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        return message

    async def list_recent(self, user_id: str | None = None, limit: int = 20) -> list[Conversation]:
        q = (
            select(Conversation)
            .options(_WITHOUT_MESSAGES)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        if user_id:
            q = q.where(Conversation.user_id == user_id)
        else:
            q = q.where(Conversation.user_id.is_(None))
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def delete(self, conversation_id: str) -> bool:
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return False
        await self.db.delete(conversation)
        return True
