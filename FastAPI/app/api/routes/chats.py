from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/chats", tags=["Chats"])

@router.post("/", response_model=ChatResponse)
async def chat_interaction(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a chat message from the user.
    Creates conversation if not exists, saves user message,
    generates bot response via LLM + RAG, and saves references.
    """
    chat_service = ChatService(db)
    response = await chat_service.process_chat(current_user.id, request)
    return response

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = Query(20, le=100),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List interactions/conversations for the current user."""
    chat_service = ChatService(db)
    conversations = chat_service.list_conversations(current_user.id, limit, offset)
    return conversations

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get history of a specific conversation."""
    chat_service = ChatService(db)
    conversation = chat_service.get_conversation(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation
