from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None
    temperature: float = 0.7


class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    sources: List[dict] = []


class MessageHistory(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ConversationHistory(BaseModel):
    conversation_id: int
    title: str
    messages: List[MessageHistory]
    created_at: datetime
    updated_at: datetime
