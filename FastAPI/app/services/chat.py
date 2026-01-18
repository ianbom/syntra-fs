from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException

from app.models.chat import Conversation, Chat, ChatReference, ChatRole
from app.models.document_chunk import DocumentChunk
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.llm import generate_response
from app.services.embedding import generate_embedding

class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, user_id: int, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

    def list_conversations(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    async def process_chat(self, user_id: int, request: ChatRequest) -> ChatResponse:
        # 1. Handle Conversation
        if request.conversation_id:
            conversation = self.get_conversation(request.conversation_id, user_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation with title from first 5 words
            title = " ".join(request.message.split()[:5])
            conversation = self.create_conversation(user_id, title)

        # 2. Save User Message
        user_chat = Chat(
            conversation_id=conversation.id,
            role=ChatRole.USER,
            message=request.message
        )
        self.db.add(user_chat)
        self.db.commit()

        # 3. RAG: Retrieve Context
        query_embedding = generate_embedding(request.message)
        
        # Search for similar chunks (top 5) using cosine distance (l2_distance for normalized vectors is fine)
        # Assuming pgvector is set up.
        # Note: distance <-> similarity. Lower L2 distance is better.
        chunks = self.db.query(DocumentChunk).order_by(
            DocumentChunk.embedding.l2_distance(query_embedding)
        ).limit(5).all()

        context_text = "\n\n".join([c.content for c in chunks])
        
        # 4. Construct Prompt
        system_prompt = (
            "You are a helpful AI assistant for knowledge base queries. "
            "Use the following context to answer the user's question. "
            "If the answer is not in the context, say you don't know."
        )
        full_prompt = f"{system_prompt}\n\nContext:\n{context_text}\n\nUser: {request.message}\nAssistant:"

        # 5. Generate Response
        answer = await generate_response(full_prompt)

        # 6. Save Bot Message
        bot_chat = Chat(
            conversation_id=conversation.id,
            role=ChatRole.BOT,
            message=answer
        )
        self.db.add(bot_chat)
        self.db.commit()
        self.db.refresh(bot_chat)

        # 7. Save References
        for chunk in chunks:
            # Calculate a relevance score (simple inverse distance or just placeholder)
            # l2_distance returns distance, so similarity ~ 1/(1+dist) or just store distance
            # For now, we'll iterate and manually calculate or just link them.
            # Since we can't easily get the distance value from the ORM object without extra query fields,
            # we'll skip score for now or do a separate query if needed. 
            # We will just link them.
            
            reference = ChatReference(
                chat_id=bot_chat.id,
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                relevance_score=0.9, # Placeholder or need advanced query to get actual distance
                quote=chunk.content[:200], # Store preview
                page_number=chunk.page_number
            )
            self.db.add(reference)
        
        self.db.commit()
        self.db.refresh(bot_chat)

        return ChatResponse(
            id=bot_chat.id,
            conversation_id=conversation.id,
            role=bot_chat.role,
            message=bot_chat.message,
            created_at=bot_chat.created_at,
            references=[] # We can add references if we want to return them immediately, need to be converted to Pydantic models
        )
