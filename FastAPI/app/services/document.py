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
from app.services.metadata_extractor import (
    extract_metadata_with_llm,
    is_metadata_incomplete,
    merge_metadata
)

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
                await progress_callback(30, "Extracting metadata with GROBID...")
            
            metadata = await self._extract_metadata(file_content, progress_callback)
            
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
    
    async def _extract_metadata(self, file_content: bytes, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Extract and format metadata from PDF using GROBID + LLM fallback."""
        # Step 1: Extract with GROBID
        header = extract_header(file_content)
        references = extract_references(file_content)
        fulltext = extract_fulltext(file_content)
        print('================================fulltext dari grobid================================')
        print(fulltext)
        print('=====================================')
        
        metadata = format_for_database(header, references)
        metadata["fulltext"] = fulltext or ""
        
        # Step 2: Extract raw PDF text for LLM (includes title page)
        raw_pdf_text = self._extract_raw_pdf_text(file_content)
        
        # Step 3: Check if metadata is incomplete and use LLM fallback
        if is_metadata_incomplete(metadata):
            print("Metadata incomplete from GROBID, using LLM fallback...")
            if progress_callback:
                await progress_callback(45, "Extracting metadata with LLM (GROBID incomplete)...")
            
            # Use raw PDF text for LLM (not GROBID fulltext) to ensure title page is included
            llm_input_text = raw_pdf_text if raw_pdf_text else (fulltext or "")
            # print('=============llm_input_text============')
            # print(llm_input_text)
            # print('====================================')
            # print('=============fulltext============')
            # print(fulltext)
            # print('=============raw_pdf_text============')
            # print(raw_pdf_text)
            try:
                llm_metadata = await extract_metadata_with_llm(llm_input_text, metadata)
                print('=============llm_metadata============')
                print(llm_metadata)
                print('=============metadata============')
                print(metadata)
                if llm_metadata:
                    metadata = merge_metadata(metadata, llm_metadata)
                    print("LLM metadata merge complete")
            except Exception as e:
                print(f"LLM metadata extraction failed: {str(e)}")
                # Continue with GROBID metadata only
        
        # Step 4: Final validation - ensure critical fields are never empty
        raw_text_for_fallback = raw_pdf_text if raw_pdf_text else (fulltext or "")
        metadata = self._validate_metadata(metadata, raw_text_for_fallback)
        
        return metadata
    
    def _extract_raw_pdf_text(self, file_content: bytes) -> str:
        """
        Extract raw text from PDF using PyMuPDF.
        Returns ALL pages as plain text, preserving page order.
        This ensures the title page (page 1) is always included.
        """
        # Try both import names (pymupdf for v1.25+, fitz for older)
        pymupdf = None
        try:
            import pymupdf as pymupdf
        except ImportError:
            try:
                import fitz as pymupdf
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="PyMuPDF is not installed. Run: pip install PyMuPDF"
                )
        
        try:
            doc = pymupdf.open(stream=file_content, filetype="pdf")
            pages_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if text and text.strip():
                    pages_text.append(text.strip())
            
            doc.close()
            
            raw_text = "\n\n".join(pages_text)
            print(f"  PyMuPDF: Extracted {len(raw_text)} chars from {len(pages_text)} pages")
            print(f"  PyMuPDF first 200 chars: {raw_text[:200]}")
            return raw_text
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"PDF text extraction failed: {str(e)}"
            )
    
    def _validate_metadata(self, metadata: Dict[str, Any], fulltext: str) -> Dict[str, Any]:
        """
        Final validation: ensure no critical field is empty.
        Generates fallback values if GROBID + LLM both failed.
        """
        # Title: MUST exist
        title = metadata.get("title")
        if not title or title.strip() == "" or title.strip().lower() in ["untitled", "untitled document"]:
            # Last resort: derive from first line of fulltext
            if fulltext:
                first_line = fulltext.strip().split('\n')[0][:150].strip()
                if first_line and len(first_line) > 10:
                    metadata["title"] = first_line
                    print(f"  Fallback title from first line: {first_line[:80]}")
                else:
                    metadata["title"] = f"Document-{hash(fulltext[:500]) % 100000}"
                    print(f"  Fallback title from hash: {metadata['title']}")
            else:
                metadata["title"] = "Document tanpa judul"
        
        # Keywords: should exist
        if not metadata.get("keywords"):
            # Extract from title
            title_words = metadata["title"].split()
            keywords = [w for w in title_words if len(w) > 3][:5]
            if keywords:
                metadata["keywords"] = ", ".join(keywords)
                print(f"  Fallback keywords from title: {metadata['keywords']}")
        
        # Language: default to Indonesian if empty
        if not metadata.get("language"):
            metadata["language"] = "id"
            print("  Fallback language: id")
        
        # Description: generate from abstract or content
        if not metadata.get("description") and metadata.get("abstract"):
            metadata["description"] = metadata["abstract"][:200]
            print("  Fallback description from abstract")
        
        # Parse date string from LLM if it's a string
        if isinstance(metadata.get("date"), str):
            from datetime import datetime
            date_str = metadata["date"]
            parsed = None
            for fmt in ["%Y-%m-%d", "%Y-%m", "%Y", "%d %B %Y", "%B %Y"]:
                try:
                    parsed = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            metadata["date"] = parsed
        
        print(f"  Final metadata validation complete. Title: {str(metadata.get('title', ''))[:80]}")
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
