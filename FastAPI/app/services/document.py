"""Document processing service - handles PDF upload, GROBID extraction, and embedding."""
import uuid
from io import BytesIO
from datetime import timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from app.config import get_settings
from app.models.document import Document, DocumentType
from app.models.document_chunk import DocumentChunk, ChunkType
from app.services.grobid import extract_header, extract_fulltext, extract_references, format_for_database
from app.services.embedding import generate_embedding
from app.services.minio import get_minio_client

settings = get_settings()

# Constants
MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50
WORDS_PER_PAGE = 500


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ChunkData:
    """Data class for chunk information."""
    chunk_index: int
    content: str
    token_count: int
    chunk_type: ChunkType
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    chunk_metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# File Validation
# =============================================================================

class FileValidator:
    """Handles file validation logic."""
    
    @staticmethod
    def validate_pdf(file: UploadFile) -> None:
        """Validate that file is a PDF."""
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
    
    @staticmethod
    def validate_size(content: bytes) -> None:
        """Validate file size."""
        if len(content) > MAX_PDF_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_PDF_SIZE // (1024 * 1024)}MB"
            )


# =============================================================================
# MinIO Storage Operations
# =============================================================================

class MinIOStorage:
    """Handles MinIO storage operations."""
    
    def __init__(self):
        self.client = get_minio_client()
        self.bucket = settings.MINIO_DOCUMENTS_BUCKET
    
    def ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")
    
    def upload_file(self, content: bytes, original_filename: str) -> str:
        """Upload file to MinIO. Returns unique filename."""
        extension = original_filename.split(".")[-1].lower() if original_filename else "pdf"
        unique_filename = f"{uuid.uuid4()}.{extension}"
        
        self.ensure_bucket_exists()
        
        try:
            self.client.put_object(
                self.bucket,
                unique_filename,
                BytesIO(content),
                length=len(content),
                content_type="application/pdf"
            )
            return unique_filename
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from MinIO."""
        try:
            self.client.remove_object(self.bucket, file_path)
            return True
        except Exception:
            return False
    
    def get_download_url(self, file_path: str, expires_hours: int = 1) -> str:
        """Get presigned download URL."""
        try:
            return self.client.presigned_get_object(
                self.bucket,
                file_path,
                expires=timedelta(hours=expires_hours)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get download URL: {str(e)}")


# =============================================================================
# Text Chunking
# =============================================================================

class TextChunker:
    """Handles text chunking with metadata."""
    
    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, document_title: str = None) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks with metadata."""
        if not text or not text.strip():
            return []
        
        text = text.strip()
        words = text.split()
        total_words = len(words)
        
        chunks = []
        start = 0
        chunk_index = 0
        
        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_content = " ".join(chunk_words)
            
            if chunk_content.strip():
                chunks.append(self._create_chunk_dict(
                    chunk_index=chunk_index,
                    content=chunk_content,
                    word_count=len(chunk_words),
                    word_start=start,
                    word_end=min(end, total_words),
                    total_words=total_words,
                    document_title=document_title
                ))
                chunk_index += 1
            
            start = end - self.overlap if end < len(words) else len(words)
        
        return chunks
    
    def _create_chunk_dict(
        self, 
        chunk_index: int, 
        content: str, 
        word_count: int,
        word_start: int,
        word_end: int,
        total_words: int,
        document_title: str = None
    ) -> Dict[str, Any]:
        """Create chunk dictionary with metadata."""
        estimated_page = (word_start // WORDS_PER_PAGE) + 1
        
        return {
            "chunk_index": chunk_index,
            "content": content,
            "token_count": word_count,
            "chunk_type": ChunkType.PARAGRAPH,
            "page_number": estimated_page,
            "section_title": None,
            "chunk_metadata": {
                "source_document": document_title,
                "word_start": word_start,
                "word_end": word_end,
                "total_words": total_words,
                "relative_position": round(word_start / total_words, 3) if total_words > 0 else 0,
                "chunk_size": word_count,
                "has_overlap": word_start > 0
            }
        }
    
    @staticmethod
    def create_title_chunk(title: str, creator: str = None, doi: str = None) -> Dict[str, Any]:
        """Create special chunk for document title."""
        return {
            "chunk_index": 0,
            "content": title,
            "token_count": len(title.split()),
            "chunk_type": ChunkType.TITLE,
            "page_number": 1,
            "section_title": "Title",
            "chunk_metadata": {
                "source_document": title,
                "section": "title",
                "is_header": True,
                "authors": creator,
                "doi": doi
            }
        }
    
    @staticmethod
    def create_abstract_chunk(abstract: str, document_title: str = None) -> Dict[str, Any]:
        """Create special chunk for abstract."""
        return {
            "chunk_index": 0,
            "content": abstract,
            "token_count": len(abstract.split()),
            "chunk_type": ChunkType.ABSTRACT,
            "page_number": 1,
            "section_title": "Abstract",
            "chunk_metadata": {
                "source_document": document_title,
                "section": "abstract",
                "is_summary": True,
                "word_count": len(abstract.split())
            }
        }
    
    @staticmethod
    def reindex_chunks(chunks: List[Dict[str, Any]]) -> None:
        """Re-index chunks after insertion."""
        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i


# =============================================================================
# Document Builder
# =============================================================================

class DocumentBuilder:
    """Builds Document model from metadata."""
    
    @staticmethod
    def build_from_metadata(
        metadata: Dict[str, Any],
        file_path: str,
        document_type: DocumentType,
        is_private: bool
    ) -> Document:
        """Create Document model from metadata dictionary."""
        return Document(
            title=metadata["title"],
            creator=metadata["creator"],
            keywords=metadata["keywords"],
            description=metadata["description"],
            publisher=metadata["publisher"],
            contributor=metadata["contributor"],
            date=metadata["date"],
            type=document_type,
            format=metadata["format"],
            identifier=metadata["identifier"],
            source=metadata["source"],
            language=metadata["language"],
            relation=metadata["relation"],
            doi=metadata["doi"],
            abstract=metadata["abstract"],
            citation_count=metadata["citation_count"],
            file_path=file_path,
            is_private=is_private,
            is_metadata_complete=bool(metadata["title"] and metadata["creator"])
        )


# =============================================================================
# Chunk Processor
# =============================================================================

class ChunkProcessor:
    """Processes chunks and creates embeddings."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_chunks(
        self, 
        document: Document, 
        chunks: List[Dict[str, Any]],
        progress_callback: Optional[Callable] = None
    ) -> None:
        """Generate embeddings and save chunks to database."""
        total_chunks = len(chunks)
        
        for i, chunk_data in enumerate(chunks):
            # Progress update
            if progress_callback and i % 5 == 0:
                percent = 60 + int((i / total_chunks) * 30)
                await progress_callback(percent, f"Generating embeddings for chunk {i+1}/{total_chunks}...")
            
            # Generate embedding
            embedding = generate_embedding(chunk_data["content"])
            
            # Create chunk record
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
                embedding=embedding,
                chunk_type=chunk_data["chunk_type"],
                page_number=chunk_data.get("page_number"),
                section_title=chunk_data.get("section_title"),
                chunk_metadata=chunk_data.get("chunk_metadata")
            )
            self.db.add(chunk)


# =============================================================================
# Main Document Service
# =============================================================================

class DocumentService:
    """Main service for document processing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage = MinIOStorage()
        self.chunker = TextChunker()
        self.chunk_processor = ChunkProcessor(db)
    
    async def process_document(
        self,
        file: UploadFile,
        document_type: DocumentType = DocumentType.JOURNAL,
        is_private: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Document:
        """
        Full document processing pipeline.
        
        Steps:
        1. Validate PDF
        2. Upload to MinIO
        3. Extract metadata via GROBID
        4. Create document record
        5. Create chunks with embeddings
        """
        # Step 1: Validate
        FileValidator.validate_pdf(file)
        file_content = await file.read()
        FileValidator.validate_size(file_content)
        
        # Step 2: Upload to storage
        if progress_callback:
            await progress_callback(10, "Uploading document to storage...")
        file_path = self.storage.upload_file(file_content, file.filename)
        
        try:
            # Step 3: Extract metadata
            if progress_callback:
                await progress_callback(30, "Extracting metadata with AI...")
            
            metadata = self._extract_metadata(file_content)
            
            # Step 4: Create document record
            document = DocumentBuilder.build_from_metadata(
                metadata, file_path, document_type, is_private
            )
            self.db.add(document)
            self.db.flush()
            
            # Step 5: Process chunks
            if progress_callback:
                await progress_callback(60, "Processing content chunks...")
            
            chunks = self._prepare_chunks(metadata)
            await self.chunk_processor.process_chunks(document, chunks, progress_callback)
            
            # Commit and finish
            self.db.commit()
            self.db.refresh(document)
            
            if progress_callback:
                await progress_callback(100, "Document processing complete!")
            
            return document
            
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            self.storage.delete_file(file_path)
            raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
    
    def _extract_metadata(self, file_content: bytes) -> Dict[str, Any]:
        """Extract and format metadata from PDF."""
        header = extract_header(file_content)
        references = extract_references(file_content)
        fulltext = extract_fulltext(file_content)
        
        metadata = format_for_database(header, references)
        metadata["fulltext"] = fulltext
        return metadata
    
    def _prepare_chunks(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare all chunks including title, abstract, and content."""
        # Get content chunks
        chunks = self.chunker.chunk_text(
            metadata.get("fulltext", ""),
            document_title=metadata["title"]
        )
        
        # Add abstract chunk
        if metadata.get("abstract"):
            abstract_chunk = TextChunker.create_abstract_chunk(
                metadata["abstract"],
                metadata["title"]
            )
            chunks.insert(0, abstract_chunk)
            TextChunker.reindex_chunks(chunks)
        
        # Add title chunk
        if metadata.get("title"):
            title_chunk = TextChunker.create_title_chunk(
                metadata["title"],
                metadata.get("creator"),
                metadata.get("doi")
            )
            chunks.insert(0, title_chunk)
            TextChunker.reindex_chunks(chunks)
        
        return chunks


# =============================================================================
# Public API Functions (for backward compatibility)
# =============================================================================

async def process_document(
    file: UploadFile,
    db: Session,
    document_type: DocumentType = DocumentType.JOURNAL,
    is_private: bool = False,
    progress_callback: Optional[Callable] = None
) -> Document:
    """Process document - wrapper for backward compatibility."""
    service = DocumentService(db)
    return await service.process_document(file, document_type, is_private, progress_callback)


def get_document_download_url(file_path: str) -> str:
    """Get presigned URL for downloading a document."""
    storage = MinIOStorage()
    return storage.get_download_url(file_path)


def delete_document_file(file_path: str) -> bool:
    """Delete document file from MinIO."""
    storage = MinIOStorage()
    return storage.delete_file(file_path)


# Legacy function exports
def ensure_documents_bucket_exists(client) -> None:
    """Legacy: Create documents bucket if it doesn't exist."""
    storage = MinIOStorage()
    storage.ensure_bucket_exists()


async def upload_pdf_to_minio(file_content: bytes, original_filename: str) -> str:
    """Legacy: Upload PDF to MinIO."""
    storage = MinIOStorage()
    return storage.upload_file(file_content, original_filename)


def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, overlap: int = DEFAULT_CHUNK_OVERLAP, document_title: str = None) -> list[dict]:
    """Legacy: Split text into chunks."""
    chunker = TextChunker(chunk_size, overlap)
    return chunker.chunk_text(text, document_title)
