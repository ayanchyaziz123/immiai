from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    conversation_id: Optional[str] = None
    language: str = Field(default="English")
    visa_type: str = Field(default="Any")
    document_type: str = Field(default="None")
    category: str = Field(default="General")
    document_text: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Paste USCIS document / RFE text for context-aware answers",
    )


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    message_id: str
    model_version: str
    processing_time_ms: int


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}
