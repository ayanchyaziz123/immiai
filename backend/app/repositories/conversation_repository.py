from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.conversation import Conversation, Message, Role


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def create(self, title: str) -> Conversation:
        conversation = Conversation(title=title)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_or_create(self, conversation_id: str | None, title: str) -> Conversation:
        if conversation_id:
            existing = await self.get_by_id(conversation_id)
            if existing:
                return existing
        return await self.create(title)

    async def add_message(
        self, conversation_id: str, role: Role, content: str
    ) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)
        return message

    async def list_recent(self, limit: int = 50) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, conversation_id: str) -> bool:
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return False
        await self.db.delete(conversation)
        return True
