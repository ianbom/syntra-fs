from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.chat import ChatService
from app.config import get_settings

router = APIRouter(prefix="/chats", tags=["Chats"])
settings = get_settings()

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


@router.get("/models/embedding")
async def list_embedding_models():
    """
    List all available Google Gemini embedding models.
    Returns models that support 'embedContent' method.
    """
    api_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(status_code=500, detail="Google API key not configured")
    
    try:
        genai.configure(api_key=api_key)
        
        embedding_models = []
        generation_models = []
        
        for m in genai.list_models():
            methods = m.supported_generation_methods
            
            model_info = {
                "name": m.name,
                "display_name": m.display_name,
                "description": m.description,
                "supported_methods": methods
            }
            
            # Categorize models
            if 'embedContent' in methods:
                embedding_models.append(model_info)
            if 'generateContent' in methods:
                generation_models.append(model_info)
        
        return {
            "current_embedding_model": settings.GOOGLE_EMBEDDING_MODEL,
            "current_generation_model": settings.GOOGLE_GENERATION_MODEL,
            "embedding_models": embedding_models,
            "generation_models": generation_models
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")