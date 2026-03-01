"""API routes for document management."""
from typing import Optional, List
from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.document import Document, DocumentType
from app.models.document_chunk import DocumentChunk
from app.schemas.document import (
    DocumentUpload,
    DocumentResponse,
    DocumentListItem,
    DocumentListResponse,
    DocumentUpdate,
    DocumentTypeEnum
)
from app.services.document import (
    process_document,
    get_document_download_url,
    delete_document_file,
    FileValidator,
    MinIOStorage
)
from app.websockets import manager
from fastapi import WebSocket
from app.services.grobid import extract_header, extract_fulltext, extract_references
from app.tasks.document_tasks import process_document_task

router = APIRouter(prefix="/documents", tags=["Documents"])


def _build_document_response(document: Document, chunk_count: int) -> DocumentResponse:
    """Helper function to build DocumentResponse from Document model."""
    return DocumentResponse(
        id=document.id,
        title=document.title,
        creator=document.creator,
        keywords=document.keywords,
        description=document.description,
        publisher=document.publisher,
        contributor=document.contributor,
        publication_date=document.date,
        type=DocumentTypeEnum(document.type.value) if document.type else DocumentTypeEnum.JOURNAL,
        format=document.format,
        identifier=document.identifier,
        source=document.source,
        language=document.language,
        relation=document.relation,
        coverage=document.coverage,
        rights=document.rights,
        doi=document.doi,
        abstract=document.abstract,
        citation_count=document.citation_count or 0,
        file_path=document.file_path,
        is_private=document.is_private or False,
        is_metadata_complete=document.is_metadata_complete or False,
        processing_status=document.processing_status or "completed",
        processing_error=document.processing_error,
        created_at=document.created_at,
        updated_at=document.updated_at,
        chunk_count=chunk_count
    )


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(client_id)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    type: DocumentTypeEnum = Query(default=DocumentTypeEnum.JOURNAL),
    is_private: bool = Query(default=False),
    client_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Upload and process a PDF document.
    
    The document will be:
    1. Validated and stored in MinIO (instant)
    2. Processed in background by Celery worker (GROBID, LLM, embeddings)
    
    Returns immediately with processing_status='processing'.
    Use GET /documents/{id}/status to poll for completion.
    """
    # Step 1: Validate file
    FileValidator.validate_pdf(file)
    file_content = await file.read()
    FileValidator.validate_size(file_content)
    
    # Step 2: Upload to MinIO (fast)
    storage = MinIOStorage()
    file_path = storage.upload_file(file_content, file.filename)
    
    # Step 3: Create document record with status="processing"
    doc_type = DocumentType(type.value)
    document = Document(
        title="Sedang diproses...",
        file_path=file_path,
        type=doc_type,
        is_private=is_private,
        format="application/pdf",
        processing_status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Step 4: Send processing task to Celery (non-blocking)
    process_document_task.delay(document.id, file_path)
    print(f"Celery task dispatched for document {document.id}")
    
    # Notify via WebSocket
    if client_id:
        await manager.send_personal_message(
            {"status": "processing", "progress": 10, "message": "Document uploaded, processing started...", "document_id": document.id},
            client_id
        )
    
    return _build_document_response(document, 0)


@router.get("/{document_id}/status")
async def get_document_status(
    document_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the processing status of a document.
    Used by frontend to poll for completion after upload.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunk_count = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.document_id == document.id
    ).scalar() or 0
    
    return {
        "id": document.id,
        "title": document.title,
        "processing_status": document.processing_status,
        "processing_error": document.processing_error,
        "chunk_count": chunk_count,
        "is_metadata_complete": document.is_metadata_complete or False
    }


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    type: Optional[DocumentTypeEnum] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all documents with pagination.
    Optionally filter by type or search in title/creator.
    """
    query = db.query(Document)
    
    # Apply filters
    if type:
        query = query.filter(Document.type == DocumentType(type.value))
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Document.title.ilike(search_term)) |
            (Document.creator.ilike(search_term)) |
            (Document.keywords.ilike(search_term))
        )
    
    # Get total count
    total = query.count()
    
    # Paginate
    offset = (page - 1) * per_page
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Calculate total pages
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    
    return DocumentListResponse(
        documents=[
            DocumentListItem(
                id=doc.id,
                title=doc.title,
                creator=doc.creator,
                publication_date=doc.date,
                type=DocumentTypeEnum(doc.type.value),
                doi=doc.doi,
                is_private=doc.is_private,
                created_at=doc.created_at
            )
            for doc in documents
        ],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get a document by ID with full metadata."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    chunk_count = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.document_id == document.id
    ).scalar() or 0
    
    return _build_document_response(document, chunk_count)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    update_data: DocumentUpdate,
    db: Session = Depends(get_db)
):
    """Update document metadata."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field == "type" and value:
            setattr(document, field, DocumentType(value.value))
        else:
            setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    chunk_count = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.document_id == document.id
    ).scalar() or 0
    
    return _build_document_response(document, chunk_count)


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document and its chunks."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from MinIO
    if document.file_path:
        delete_document_file(document.file_path)
    
    # Delete from database (chunks will cascade)
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully", "id": document_id}


@router.get("/{document_id}/download")
async def download_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Get download URL for a document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not document.file_path:
        raise HTTPException(status_code=404, detail="Document file not found")
    
    download_url = get_document_download_url(document.file_path)
    
    return {
        "download_url": download_url,
        "filename": f"{document.title}.pdf"
    }



@router.post("/upload-bulk")
async def upload_documents_bulk(
    files: List[UploadFile] = File(...),
    type: DocumentTypeEnum = Query(default=DocumentTypeEnum.JOURNAL),
    is_private: bool = Query(default=False),
    client_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Upload and process multiple PDF documents at once.
    
    Each document will be:
    1. Stored in MinIO
    2. Processed by GROBID for metadata extraction
    3. Split into chunks with embeddings for semantic search
    
    Returns a list of results for each uploaded document.
    """
    doc_type = DocumentType(type.value)
    results = []
    total_files = len(files)
    
    for index, file in enumerate(files):
        file_result = {
            "filename": file.filename,
            "status": "pending",
            "document": None,
            "error": None
        }
        
        try:
            async def progress_callback(progress: int, message: str):
                if client_id:
                    overall_progress = int(((index + (progress / 100)) / total_files) * 100)
                    await manager.send_personal_message(
                        {
                            "status": "processing",
                            "current_file": file.filename,
                            "file_index": index + 1,
                            "total_files": total_files,
                            "file_progress": progress,
                            "overall_progress": overall_progress,
                            "message": message
                        },
                        client_id
                    )
            
            document = await process_document(
                file=file,
                db=db,
                document_type=doc_type,
                is_private=is_private,
                progress_callback=progress_callback
            )
            
            chunk_count = db.query(func.count(DocumentChunk.id)).filter(
                DocumentChunk.document_id == document.id
            ).scalar() or 0
            
            file_result["status"] = "success"
            file_result["document"] = _build_document_response(document, chunk_count)
            
        except Exception as e:
            file_result["status"] = "error"
            file_result["error"] = str(e)
        
        results.append(file_result)
    
    if client_id:
        await manager.send_personal_message(
            {
                "status": "complete",
                "overall_progress": 100,
                "message": f"Completed processing {total_files} files",
                "success_count": sum(1 for r in results if r["status"] == "success"),
                "error_count": sum(1 for r in results if r["status"] == "error")
            },
            client_id
        )
    
    return {
        "total": total_files,
        "success_count": sum(1 for r in results if r["status"] == "success"),
        "error_count": sum(1 for r in results if r["status"] == "error"),
        "results": results
    }

@router.post("/test-grobid-header")
async def test_grobid_header(file: UploadFile = File(...)):
    file_bytes = await file.read()
    header = await extract_header(file_bytes)
    print(header)
    return {"header": header}

@router.post("/test-grobid-full")
async def test_grobid_full(file: UploadFile = File(...)):
    file_bytes = await file.read()
    fulltext = extract_fulltext(file_bytes)
    with open("grobid_fulltext_response.txt", "w", encoding="utf-8") as f:
        f.write("==grobid_fulltext_response \n")
        f.write(fulltext + "\n")
        f.write("=====================================\n")
    return { 
        "length": len(fulltext),
        "fulltext": fulltext}

@router.post("/test-grobid-references")
async def test_grobid_references(file: UploadFile = File(...)):
    file_bytes = await file.read()
    references = extract_references(file_bytes)
    print(references)
    return {"references": references}

@router.post("/test-pymupdf")
async def test_pymupdf(file: UploadFile = File(...)):
    file_bytes = await file.read()

    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            raise HTTPException(status_code=500, detail="PyMuPDF not installed")

    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text and text.strip():
            pages.append({
                "page": page_num + 1,
                "text": text.strip()
            })
    doc.close()

    full_text = "\n\n".join([p["text"] for p in pages])
    print(f"PyMuPDF: {len(full_text)} chars from {len(pages)} pages")


    with open("pymupdf_response.txt", "w", encoding="utf-8") as f:
        f.write("==pymupdf_response \n")
        f.write(full_text + "\n")
        f.write("=====================================\n")

    return {
        "total_pages": len(pages),
        "total_chars": len(full_text),
        "full_text": full_text,
        "per_page": pages
    }
