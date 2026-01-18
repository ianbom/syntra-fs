from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel

class ChatReferenceResponse(BaseModel):
    id: int
    document_id: int
    chunk_id: int
    relevance_score: float
    quote: str
    page_number: Optional[int]
    document_title: str
    file_path: Optional[str] = None

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "bot"]
    message: str
    created_at: datetime
    references: List[ChatReferenceResponse] = []

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: int
    title: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime
    chats: List[ChatResponse] = []

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
