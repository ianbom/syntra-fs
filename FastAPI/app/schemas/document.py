"""Pydantic schemas for Document API."""
from datetime import date as DateType, datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class DocumentTypeEnum(str, Enum):
    """Document type enumeration."""
    JOURNAL = "journal"
    CONFERENCE = "conference"
    THESIS = "thesis"
    REPORT = "report"
    BOOK = "book"


class DocumentUpload(BaseModel):
    """Schema for document upload request."""
    type: DocumentTypeEnum = DocumentTypeEnum.JOURNAL
    is_private: bool = False


class DocumentBase(BaseModel):
    """Base document schema with Dublin Core metadata."""
    model_config = ConfigDict(from_attributes=True)
    
    title: str
    creator: Optional[str] = None
    keywords: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    contributor: Optional[str] = None
    publication_date: Optional[DateType] = Field(default=None, alias="date")
    type: DocumentTypeEnum = DocumentTypeEnum.JOURNAL
    format: Optional[str] = None
    identifier: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    relation: Optional[str] = None
    coverage: Optional[str] = None
    rights: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: int = 0


class DocumentCreate(DocumentBase):
    """Schema for creating a document manually."""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    title: Optional[str] = None
    creator: Optional[str] = None
    keywords: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    contributor: Optional[str] = None
    publication_date: Optional[DateType] = Field(default=None, alias="date")
    type: Optional[DocumentTypeEnum] = None
    source: Optional[str] = None
    language: Optional[str] = None
    relation: Optional[str] = None
    coverage: Optional[str] = None
    rights: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    is_private: Optional[bool] = None


class DocumentResponse(BaseModel):
    """Schema for document response."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: int
    title: str
    creator: Optional[str] = None
    keywords: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    contributor: Optional[str] = None
    publication_date: Optional[DateType] = Field(default=None, alias="date")
    type: DocumentTypeEnum = DocumentTypeEnum.JOURNAL
    format: Optional[str] = None
    identifier: Optional[str] = None
    source: Optional[str] = None
    language: Optional[str] = None
    relation: Optional[str] = None
    coverage: Optional[str] = None
    rights: Optional[str] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    citation_count: int = 0
    file_path: Optional[str] = None
    is_private: bool = False
    is_metadata_complete: bool = False
    processing_status: str = "completed"
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    chunk_count: int = 0


class DocumentListItem(BaseModel):
    """Schema for document list item (lightweight)."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: int
    title: str
    creator: Optional[str] = None
    publication_date: Optional[DateType] = Field(default=None, alias="date")
    type: DocumentTypeEnum
    doi: Optional[str] = None
    is_private: bool = False
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Schema for paginated document list."""
    documents: list[DocumentListItem]
    total: int
    page: int
    per_page: int
    pages: int


class DocumentSearchQuery(BaseModel):
    """Schema for document search query."""
    query: Optional[str] = None
    type: Optional[DocumentTypeEnum] = None
    creator: Optional[str] = None
    keywords: Optional[str] = None
    date_from: Optional[DateType] = None
    date_to: Optional[DateType] = None
