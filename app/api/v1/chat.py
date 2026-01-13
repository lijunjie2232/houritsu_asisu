from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db.base import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ConversationHistory
from app.services.chat_service import (get_conversation_history,
                                       get_user_conversations,
                                       process_chat_request)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/message", response_model=ChatResponse)
def chat(chat_request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and receive a response from the Japanese law AI agent"""
    try:
        response = process_chat_request(db, chat_request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}", response_model=ConversationHistory)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Get the history of a specific conversation"""
    history = get_conversation_history(db, conversation_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return history


@router.get("/user/{user_id}/conversations", response_model=List[ConversationHistory])
def get_conversations(user_id: int, db: Session = Depends(get_db)):
    """Get all conversations for a specific user"""
    return get_user_conversations(db, user_id)
