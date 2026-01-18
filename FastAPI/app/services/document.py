"""Document processing service - handles PDF upload, GROBID extraction, and embedding."""
import uuid
from io import BytesIO
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from app.config import get_settings
from app.models.document import Document, DocumentType
from app.models.document_chunk import DocumentChunk, ChunkType
from app.services.grobid import extract_header, extract_fulltext, extract_references, format_for_database
from app.services.embedding import generate_embedding
from app.services.minio import get_minio_client

settings = get_settings()

# Maximum PDF file size: 50MB
MAX_PDF_SIZE = 50 * 1024 * 1024


def ensure_documents_bucket_exists(client) -> None:
    """Create documents bucket if it doesn't exist."""
    try:
        if not client.bucket_exists(settings.MINIO_DOCUMENTS_BUCKET):
            client.make_bucket(settings.MINIO_DOCUMENTS_BUCKET)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")


async def upload_pdf_to_minio(file_content: bytes, original_filename: str) -> str:
    """
    Upload PDF to MinIO documents bucket.
    Returns the object name (unique filename).
    """
    # Generate unique filename
    extension = original_filename.split(".")[-1].lower() if original_filename else "pdf"
    unique_filename = f"{uuid.uuid4()}.{extension}"
    
    client = get_minio_client()
    ensure_documents_bucket_exists(client)
    
    try:
        file_data = BytesIO(file_content)
        client.put_object(
            settings.MINIO_DOCUMENTS_BUCKET,
            unique_filename,
            file_data,
            length=len(file_content),
            content_type="application/pdf"
        )
        return unique_filename
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    Split text into overlapping chunks for embedding.
    Returns list of dicts with content and metadata.
    """
    if not text or not text.strip():
        return []
    
    # Clean text
    text = text.strip()
    words = text.split()
    
    chunks = []
    start = 0
    chunk_index = 0
    
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_content = " ".join(chunk_words)
        
        if chunk_content.strip():
            chunks.append({
                "chunk_index": chunk_index,
                "content": chunk_content,
                "token_count": len(chunk_words),
                "chunk_type": ChunkType.PARAGRAPH
            })
            chunk_index += 1
        
        # Move start with overlap
        start = end - overlap if end < len(words) else len(words)
    
    return chunks


async def process_document(
    file: UploadFile,
    db: Session,
    document_type: DocumentType = DocumentType.JOURNAL,
    is_private: bool = False,
    progress_callback: Optional[callable] = None
) -> Document:
    """
    Full document processing pipeline:
    1. Validate PDF
    2. Upload to MinIO
    3. Extract metadata via GROBID
    4. Create document record
    5. Create chunks with embeddings
    
    Returns the created Document object.
    """
    # Validate file
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Read file content
    file_content = await file.read()
    
    if len(file_content) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_PDF_SIZE // (1024 * 1024)}MB"
        )
    
    # Upload to MinIO
    if progress_callback:
        await progress_callback(10, "Uploading document to storage...")
    
    file_path = await upload_pdf_to_minio(file_content, file.filename)
    
    try:
        # Extract metadata via GROBID
        if progress_callback:
            await progress_callback(30, "Extracting metadata with AI...")
        header_metadata = extract_header(file_content)
        references = extract_references(file_content)
        fulltext = extract_fulltext(file_content)
        
        # Format metadata for database
        db_metadata = format_for_database(header_metadata, references)
        
        # Create document record
        document = Document(
            title=db_metadata["title"],
            creator=db_metadata["creator"],
            keywords=db_metadata["keywords"],
            description=db_metadata["description"],
            publisher=db_metadata["publisher"],
            contributor=db_metadata["contributor"],
            date=db_metadata["date"],
            type=document_type,
            format=db_metadata["format"],
            identifier=db_metadata["identifier"],
            source=db_metadata["source"],
            language=db_metadata["language"],
            relation=db_metadata["relation"],
            doi=db_metadata["doi"],
            abstract=db_metadata["abstract"],
            citation_count=db_metadata["citation_count"],
            file_path=file_path,
            is_private=is_private,
            is_metadata_complete=bool(db_metadata["title"] and db_metadata["creator"])
        )
        
        db.add(document)
        db.flush()  # Get document ID before creating chunks
        
        if progress_callback:
            await progress_callback(60, "Processing content chunks...")
        
        # Create chunks from fulltext
        text_chunks = chunk_text(fulltext)
        
        # Also add abstract as a special chunk
        if db_metadata["abstract"]:
            abstract_chunk = {
                "chunk_index": 0,
                "content": db_metadata["abstract"],
                "token_count": len(db_metadata["abstract"].split()),
                "chunk_type": ChunkType.ABSTRACT
            }
            text_chunks.insert(0, abstract_chunk)
            # Re-index other chunks
            for i, chunk in enumerate(text_chunks[1:], start=1):
                chunk["chunk_index"] = i
        
        # Also add title as a chunk
        if db_metadata["title"]:
            title_chunk = {
                "chunk_index": 0,
                "content": db_metadata["title"],
                "token_count": len(db_metadata["title"].split()),
                "chunk_type": ChunkType.TITLE
            }
            text_chunks.insert(0, title_chunk)
            # Re-index other chunks
            for i, chunk in enumerate(text_chunks[1:], start=1):
                chunk["chunk_index"] = i
        
        # Create chunk records with embeddings
        total_chunks = len(text_chunks)
        for i, chunk_data in enumerate(text_chunks):
            if progress_callback and i % 5 == 0:  # Update every 5 chunks to avoid spamming
                percent = 60 + int((i / total_chunks) * 30)  # Map 0-100% of chunks to 60-90% of total progress
                await progress_callback(percent, f"Generating embeddings for chunk {i+1}/{total_chunks}...")
            
            embedding = generate_embedding(chunk_data["content"])
            
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                token_count=chunk_data["token_count"],
                embedding=embedding,
                chunk_type=chunk_data["chunk_type"]
            )
            db.add(chunk)
        
        db.commit()
        db.refresh(document)
        
        if progress_callback:
            await progress_callback(100, "Document processing complete!")
        
        return document
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        # Try to clean up the uploaded file
        try:
            client = get_minio_client()
            client.remove_object(settings.MINIO_DOCUMENTS_BUCKET, file_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


def get_document_download_url(file_path: str) -> str:
    """Get presigned URL for downloading a document."""
    from datetime import timedelta
    
    client = get_minio_client()
    try:
        url = client.presigned_get_object(
            settings.MINIO_DOCUMENTS_BUCKET,
            file_path,
            expires=timedelta(hours=1)
        )
        return url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get download URL: {str(e)}")


def delete_document_file(file_path: str) -> bool:
    """Delete document file from MinIO."""
    client = get_minio_client()
    try:
        client.remove_object(settings.MINIO_DOCUMENTS_BUCKET, file_path)
        return True
    except Exception:
        return False
