"""Celery tasks for background document processing."""
import asyncio
from celery import shared_task
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.config import get_settings
from app.models.document import Document, DocumentType
from app.models.document_chunk import DocumentChunk, ChunkType
from app.services.grobid import (
    extract_header, extract_fulltext, extract_references,
    format_for_database, extract_structured_fulltext
)
from app.services.embedding import generate_embedding
from app.services.question_generator import generate_possibly_questions
from app.services.metadata_extractor import (
    extract_metadata_with_llm, is_metadata_incomplete, merge_metadata
)
from app.services.document import (
    MinIOStorage, extract_raw_pdf_text, validate_metadata
)
from app.services.document import SmartChunker, TextChunker

settings = get_settings()


def _run_async(coro):
    """Run an async coroutine in a sync context (for Celery)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _update_status(db: Session, document_id: int, status: str, error: str = None):
    """Update document processing status."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.processing_status = status
        if error:
            doc.processing_error = error
        db.commit()


@shared_task(name="process_document_task", bind=True, max_retries=2)
def process_document_task(self, document_id: int, file_path: str):
    """
    Background task: process a document that has already been uploaded to MinIO.
    
    Steps:
    1. Download file from MinIO
    2. Extract metadata via GROBID (+ LLM fallback)
    3. Smart chunk the document
    4. Generate embeddings for each chunk
    5. Save everything to database
    """
    db = SessionLocal()
    storage = MinIOStorage()
    
    try:
        # Update status to processing
        _update_status(db, document_id, "processing")
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            print(f"Document {document_id} not found")
            return {"status": "error", "message": "Document not found"}
        
        print(f"{'='*60}")
        print(f"CELERY TASK: Processing document {document_id} ({file_path})")
        print(f"{'='*60}")
        
        # Step 1: Download from MinIO
        print("[1/5] Downloading from MinIO...")
        file_content = storage.download_file(file_path)
        print(f"  Downloaded {len(file_content)} bytes")
        
        # Step 2: Extract metadata via GROBID
        print("[2/5] Extracting metadata with GROBID...")
        header = _run_async(extract_header(file_content))
        references = extract_references(file_content)
        fulltext = extract_fulltext(file_content)
        
        # Structured sections for smart chunking
        structured_sections = []
        try:
            structured_sections = extract_structured_fulltext(file_content)
            print(f"  Extracted {len(structured_sections)} structured sections")
        except Exception as e:
            print(f"  Structured extraction failed: {e}")
        
        metadata = format_for_database(header, references)
        metadata["fulltext"] = fulltext or ""
        metadata["structured_sections"] = structured_sections
        
        # Raw PDF text for LLM fallback + page resolution
        raw_pdf_text, pages_data = extract_raw_pdf_text(file_content)
        
        # LLM fallback if metadata incomplete
        if is_metadata_incomplete(metadata):
            print("[2b/5] Metadata incomplete, using LLM fallback...")
            llm_input_text = raw_pdf_text if raw_pdf_text else (fulltext or "")
            try:
                llm_metadata = _run_async(extract_metadata_with_llm(llm_input_text, metadata))
                if llm_metadata:
                    metadata = merge_metadata(metadata, llm_metadata)
                    print("  LLM metadata merge complete")
            except Exception as e:
                print(f"  LLM metadata extraction failed: {e}")
        
        # Validate metadata
        metadata = validate_metadata(metadata, raw_pdf_text or fulltext or "")
        
        # Update document with extracted metadata
        print("[3/5] Updating document metadata...")
        document.title = metadata["title"]
        document.creator = metadata.get("creator")
        document.keywords = metadata.get("keywords")
        document.description = metadata.get("description")
        document.publisher = metadata.get("publisher")
        document.contributor = metadata.get("contributor")
        document.date = metadata.get("date")
        document.format = metadata.get("format", "application/pdf")
        document.identifier = metadata.get("identifier")
        document.source = metadata.get("source")
        document.language = metadata.get("language")
        document.relation = metadata.get("relation")
        document.coverage = metadata.get("coverage")
        document.rights = metadata.get("rights")
        document.doi = metadata.get("doi")
        document.abstract = metadata.get("abstract")
        document.citation_count = metadata.get("citation_count", 0)
        document.is_metadata_complete = bool(metadata.get("title") and metadata.get("creator"))
        db.commit()
        
        # Step 4: Smart chunking
        print("[4/5] Chunking document...")
        
        
        chunks = []
        if structured_sections:
            print("  Using SMART CHUNKING")
            smart_chunker = SmartChunker()
            chunks = smart_chunker.chunk_structured_sections(
                sections=structured_sections,
                document_title=metadata.get("title"),
                pages_data=pages_data,
            )
        
        if not chunks:
            print("  Falling back to LEGACY CHUNKING")
            chunker = TextChunker()
            chunks = chunker.chunk_text(metadata.get("fulltext", ""), document_title=metadata["title"])
            
            # Add abstract chunk
            if metadata.get("abstract"):
                abstract_chunk = TextChunker.create_abstract_chunk(metadata["abstract"], metadata["title"])
                chunks.insert(0, abstract_chunk)
                TextChunker.reindex_chunks(chunks)
            
            # Add title chunk
            if metadata.get("title"):
                title_chunk = TextChunker.create_title_chunk(
                    metadata["title"], metadata.get("creator"), metadata.get("doi")
                )
                chunks.insert(0, title_chunk)
                TextChunker.reindex_chunks(chunks)
        
        print(f"  Created {len(chunks)} chunks")
        
        # Step 5: Generate embeddings and save chunks
        print("[5/5] Generating embeddings and saving chunks...")
        total_chunks = len(chunks)
        
        for i, chunk_data in enumerate(chunks):
            content = chunk_data["content"]
            
            # Generate content embedding
            embedding = generate_embedding(content)
            
            # Generate hypothetical questions from chunk content
            possibly_questions = None
            possibly_question_embedding = None
            try:
                section_title = chunk_data.get("section_title")
                doc_title = chunk_data.get("chunk_metadata", {}).get("source_document")
                questions = _run_async(generate_possibly_questions(
                    chunk_content=content,
                    section_title=section_title,
                    document_title=doc_title,
                ))
                if questions:
                    possibly_questions = questions
                    combined_questions = " ".join(questions)
                    possibly_question_embedding = generate_embedding(combined_questions)
                    print(f"  Chunk {i+1}: generated {len(questions)} questions")
            except Exception as e:
                print(f"  Warning: question generation failed for chunk {i+1}: {e}")
            
            # Create chunk record
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_data["chunk_index"],
                content=content,
                token_count=chunk_data["token_count"],
                embedding=embedding,
                chunk_type=chunk_data["chunk_type"],
                page_number=chunk_data.get("page_number"),
                section_title=chunk_data.get("section_title"),
                chunk_metadata=chunk_data.get("chunk_metadata"),
                possibly_questions=possibly_questions,
                possibly_question_embedding=possibly_question_embedding,
            )
            db.add(chunk)
            
            if (i + 1) % 5 == 0 or (i + 1) == total_chunks:
                print(f"  Processed chunk {i+1}/{total_chunks}")
                db.flush()
        
        # Mark as completed
        document.processing_status = "completed"
        document.processing_error = None
        db.commit()
        
        print(f"{'='*60}")
        print(f"CELERY TASK COMPLETE: Document {document_id} - {total_chunks} chunks")
        print(f"{'='*60}")
        
        return {
            "status": "completed",
            "document_id": document_id,
            "chunk_count": total_chunks,
            "title": metadata.get("title", "")[:100]
        }
        
    except Exception as e:
        db.rollback()
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f"CELERY TASK FAILED: Document {document_id} - {error_msg}")
        _update_status(db, document_id, "failed", error_msg)
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        
        return {"status": "failed", "document_id": document_id, "error": error_msg}
    
    finally:
        db.close()

