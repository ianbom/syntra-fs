from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.database import Base
import enum


class ChunkType(str, enum.Enum):
    """Chunk type enumeration for document sections."""
    TITLE = "title"
    ABSTRACT = "abstract"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    REFERENCE = "reference"


class DocumentChunk(Base):
    """Document chunk model with vector embedding for semantic search."""
    
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Chunk content
    chunk_index = Column(Integer, nullable=False)  # Order of chunk in document
    content = Column(Text, nullable=False)
    token_count = Column(Integer)
    
    # Vector embedding (nomic-embed-text dimension: 768)
    embedding = Column(Vector(768))
    
    # Hypothetical questions generated from chunk content
    possibly_questions = Column(JSONB)  # e.g. ["What is X?", "How does Y work?"]
    possibly_question_embedding = Column(Vector(768))  # Combined embedding of the questions
    
    # Additional metadata
    chunk_metadata = Column(JSONB)  # Flexible metadata storage
    page_number = Column(Integer)  # Source page number
    section_title = Column(Text)  # Section title if available
    chunk_type = Column(Enum(ChunkType), default=ChunkType.PARAGRAPH)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})>"
