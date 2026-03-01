from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime, Enum
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class DocumentType(str, enum.Enum):
    """Document type enumeration."""
    JOURNAL = "journal"
    CONFERENCE = "conference"
    THESIS = "thesis"
    REPORT = "report"
    BOOK = "book"


class Document(Base):
    """Document model with Dublin Core metadata for academic papers."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Dublin Core Metadata Elements
    title = Column(Text, nullable=False, index=True) 
    creator = Column(Text)  # Authors (comma-separated)
    keywords = Column(Text)  # Subject/Keywords
    description = Column(Text)  # Short description
    publisher = Column(Text)
    contributor = Column(Text)
    date = Column(Date)  # Publication date
    type = Column(Enum(DocumentType), default=DocumentType.JOURNAL)
    format = Column(Text)  # MIME type or file format
    identifier = Column(Text)  # Unique identifier / DOI
    source = Column(Text)  # Journal/Conference name
    language = Column(String(50))  # e.g., "en", "id"
    relation = Column(Text)  # Related resources
    coverage = Column(Text)  # Spatial/temporal coverage
    rights = Column(Text)  # Copyright info
    
    # Extended metadata
    doi = Column(String(150), unique=True, index=True, nullable=True)
    abstract = Column(Text)
    citation_count = Column(Integer, default=0)
    
    # File storage
    file_path = Column(Text)  # MinIO object name
    
    # Processing status (for background Celery tasks)
    processing_status = Column(String(20), default="completed")  # uploading, processing, completed, failed
    processing_error = Column(Text, nullable=True)  # Error message if processing failed
    
    # Status flags
    is_private = Column(Boolean, default=False)
    is_metadata_complete = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Document(id={self.id}, title='{self.title[:50]}...')>"
