from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.agents.law_agent import law_agent
from app.core.config.constants import ERROR_MESSAGES
from app.core.db.vector_db import vector_db
from app.models.conversation import Conversation, Message, User
from app.schemas.chat import (ChatRequest, ChatResponse, ConversationHistory,
                              MessageHistory)


def create_conversation(db: Session, user_id: int, title: str) -> Conversation:
    """Create a new conversation record"""
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_or_create_conversation(
    db: Session, user_id: int, conversation_id: Optional[int] = None
) -> Conversation:
    """Get existing conversation or create a new one"""
    if conversation_id:
        conversation = (
            db.query(Conversation).filter(Conversation.id == conversation_id).first()
        )
        if not conversation:
            raise ValueError(f"Conversation with id {conversation_id} not found")
    else:
        # Create a new conversation
        title = "New Legal Inquiry"  # This would ideally be generated based on the first query
        conversation = create_conversation(db, user_id, title)

    return conversation


def save_message(
    db: Session, conversation_id: int, role: str, content: str, metadata: dict = None
) -> Message:
    """Save a message to the conversation"""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        metadata_json=str(metadata) if metadata else None,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def process_chat_request(db: Session, chat_request: ChatRequest) -> ChatResponse:
    """Process a chat request using the law agent"""
    try:
        # Get or create conversation
        conversation = get_or_create_conversation(
            db, chat_request.user_id, chat_request.conversation_id
        )

        # Save user message
        save_message(db, conversation.id, "user", chat_request.message)

        # Prepare context for the agent
        # In a real implementation, we'd fetch recent conversation history

        # Query the law agent
        agent_response = law_agent.query(chat_request.message)

        # Extract the actual response text
        response_text = agent_response.get("output", str(agent_response))

        # Save assistant message
        save_message(db, conversation.id, "assistant", response_text)

        # For now, no sources are returned - this would come from the agent's tool usage
        sources = []  # Extract from agent response in a full implementation

        return ChatResponse(
            response=response_text, conversation_id=conversation.id, sources=sources
        )

    except Exception as e:
        return ChatResponse(
            response=f"{ERROR_MESSAGES['UNKNOWN_ERROR']}: {str(e)}",
            conversation_id=conversation.id if "conversation" in locals() else -1,
            sources=[],
        )


def get_conversation_history(
    db: Session, conversation_id: int
) -> Optional[ConversationHistory]:
    """Retrieve conversation history"""
    conversation = (
        db.query(Conversation).filter(Conversation.id == conversation_id).first()
    )

    if not conversation:
        return None

    # Get messages in chronological order
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
        .all()
    )

    formatted_messages = [
        MessageHistory(role=msg.role, content=msg.content, timestamp=msg.timestamp)
        for msg in messages
    ]

    return ConversationHistory(
        conversation_id=conversation.id,
        title=conversation.title,
        messages=formatted_messages,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def get_user_conversations(db: Session, user_id: int) -> List[ConversationHistory]:
    """Get all conversations for a user"""
    conversations = db.query(Conversation).filter(Conversation.user_id == user_id).all()

    result = []
    for conv in conversations:
        # Get the first message to include in conversation overview
        first_message = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.timestamp)
            .first()
        )

        result.append(
            ConversationHistory(
                conversation_id=conv.id,
                title=conv.title,
                messages=(
                    [
                        MessageHistory(
                            role=first_message.role if first_message else "",
                            content=first_message.content if first_message else "",
                            timestamp=(
                                first_message.timestamp if first_message else None
                            ),
                        )
                    ]
                    if first_message
                    else []
                ),
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )

    return result
