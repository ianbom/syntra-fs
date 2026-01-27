from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from fastapi import HTTPException

from app.models.chat import Conversation, Chat, ChatReference, ChatRole
from app.models.document_chunk import DocumentChunk
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.llm import generate_response
from app.services.embedding import generate_embedding
from app.models.document import Document

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

    def _handle_conversation(self, user_id: int, request: ChatRequest) -> Conversation:
        """Handle conversation creation or retrieval."""
        if request.conversation_id:
            conversation = self.get_conversation(request.conversation_id, user_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return conversation
        else:
            # Create new conversation with title from first 5 words
            title = " ".join(request.message.split()[:5])
            return self.create_conversation(user_id, title)

    def _save_chat_message(self, conversation_id: int, role: ChatRole, message: str) -> Chat:
        """Save a chat message to the database."""
        chat_msg = Chat(
            conversation_id=conversation_id,
            role=role,
            message=message
        )
        self.db.add(chat_msg)
        self.db.commit()
        self.db.refresh(chat_msg)
        return chat_msg

    def _retrieve_relevant_chunks(self, query: str, limit: int = 5, threshold: float = 0.3) -> tuple[List[DocumentChunk], List[float]]:
        """Retrieve relevant document chunks using embedding similarity."""
        query_embedding = generate_embedding(query)
        MIN_CONTENT_LENGTH = 50
        
        # Query chunks with cosine distance calculation
        chunks_with_distance = self.db.query(
            DocumentChunk,
            (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label('similarity')
        ).join(
            Document, DocumentChunk.document_id == Document.id
        ).filter(
            # Exclude invalid titles
            Document.title.isnot(None),
            Document.title != "",
            Document.title != "Untitled Document",
            ~Document.title.ilike("untitled%"),
            # Exclude invalid content
            DocumentChunk.content.isnot(None),
            DocumentChunk.content != "",
            func.length(DocumentChunk.content) >= MIN_CONTENT_LENGTH,
            DocumentChunk.embedding.isnot(None)
        ).order_by(
            desc('similarity')
        ).limit(limit * 2).all()  # Fetch more to filter

        chunks = []
        similarities = []
        for chunk, similarity in chunks_with_distance:
            if similarity >= threshold:
                chunks.append(chunk)
                similarities.append(similarity)
                if len(chunks) >= limit:
                    break
        
        return chunks, similarities

    def _construct_context_text(self, chunks: List[DocumentChunk]) -> str:
        """Format chunks into a context string."""
        context_parts = []
        for chunk in chunks:
            # Get document title for reference
            doc = self.db.query(Document).filter(Document.id == chunk.document_id).first()
            doc_title = doc.title if doc else "Unknown Document"
            
            context_parts.append(
                f"[Source: {doc_title}]\n{chunk.content}"
            )
        return "\n\n---\n\n".join(context_parts) if context_parts else ""

    def _construct_rag_prompt(self, message: str, context_text: str) -> str:
        """Construct the prompt for the LLM."""
        if context_text:
            system_prompt = """Anda adalah asisten AI yang membantu menjawab pertanyaan berdasarkan dokumen knowledge base.

INSTRUKSI PENTING:
1. Jawab pertanyaan user HANYA berdasarkan konteks yang diberikan di bawah ini.
2. Jika informasi tidak ditemukan dalam konteks, katakan dengan jelas bahwa informasi tersebut tidak tersedia dalam dokumen.
3. Selalu sebutkan sumber dokumen jika relevan.
4. Berikan jawaban yang jelas, terstruktur, dan informatif.
5. Gunakan bahasa yang sama dengan pertanyaan user."""

            return f"""{system_prompt}

KONTEKS DARI DOKUMEN:
{context_text}

---

PERTANYAAN USER: {message}

JAWABAN:"""
        else:
            return f"""Anda adalah asisten AI yang membantu menjawab pertanyaan berdasarkan dokumen knowledge base.

Tidak ditemukan dokumen yang relevan dengan pertanyaan user di knowledge base.

PERTANYAAN USER: {message}

Mohon beritahu user bahwa tidak ada dokumen yang relevan ditemukan dan sarankan untuk mengupload dokumen terkait atau mengajukan pertanyaan yang berbeda."""

    def _save_rag_references(self, bot_chat_id: int, chunks: List[DocumentChunk], similarities: List[float]):
        """Save references for the RAG response."""
        for i, chunk in enumerate(chunks):
            reference = ChatReference(
                chat_id=bot_chat_id,
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                relevance_score=float(similarities[i]),
                quote=chunk.content[:200],
                page_number=chunk.page_number
            )
            self.db.add(reference)
        self.db.commit()

    async def process_chat(self, user_id: int, request: ChatRequest) -> ChatResponse:
        # 1. Handle Conversation
        conversation = self._handle_conversation(user_id, request)

        # 2. Save User Message
        self._save_chat_message(conversation.id, ChatRole.USER, request.message)

        # 3. RAG: Retrieve Context
        chunks, similarities = self._retrieve_relevant_chunks(request.message)
        context_text = self._construct_context_text(chunks)
        
        # 4. Construct Prompt
        full_prompt = self._construct_rag_prompt(request.message, context_text)
        print(full_prompt)

        # 5. Generate Response
        answer = await generate_response(full_prompt)

        # 6. Save Bot Message
        bot_chat = self._save_chat_message(conversation.id, ChatRole.BOT, answer)

        # 7. Save References
        self._save_rag_references(bot_chat.id, chunks, similarities)

        return ChatResponse(
            id=bot_chat.id,
            conversation_id=conversation.id,
            role=bot_chat.role,
            message=bot_chat.message,
            created_at=bot_chat.created_at,
            references=[]
        )