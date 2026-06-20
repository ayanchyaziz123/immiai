import asyncio
import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_db, get_optional_user
from ....core.exceptions import NotFoundError
from ....models.conversation import Role
from ....repositories.conversation_repository import ConversationRepository
from ....schemas.chat import ChatRequest, ChatResponse, ConversationOut
from ....services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])
_chat_service = ChatService()


@router.post("/", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    repo = ConversationRepository(db)
    user_id = current_user.id if current_user else None

    conversation = await repo.get_or_create(
        conversation_id=request.conversation_id,
        title=request.question[:80],
        user_id=user_id,
    )
    await repo.add_message(conversation.id, Role.user, request.question)

    t0 = time.time()
    answer, model_version = await asyncio.to_thread(
        _chat_service.get_answer,
        request.question,
        request.language,
        request.visa_type,
        request.document_type,
        request.category,
        request.document_text or "",
    )
    elapsed_ms = int((time.time() - t0) * 1000)

    assistant_msg = await repo.add_message(conversation.id, Role.assistant, answer)
    await db.commit()

    return ChatResponse(
        answer             = answer,
        conversation_id    = conversation.id,
        message_id         = assistant_msg.id,
        model_version      = model_version,
        processing_time_ms = elapsed_ms,
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_optional_user),
):
    repo = ConversationRepository(db)
    user_id = current_user.id if current_user else None
    return await repo.list_recent(user_id=user_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = ConversationRepository(db)
    conversation = await repo.get_by_id(conversation_id)
    if not conversation:
        raise NotFoundError("Conversation", conversation_id)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = ConversationRepository(db)
    deleted = await repo.delete(conversation_id)
    if not deleted:
        raise NotFoundError("Conversation", conversation_id)
    await db.commit()
