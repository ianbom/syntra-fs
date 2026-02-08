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
    delete_document_file
)
from app.websockets import manager
from fastapi import WebSocket

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
    1. Stored in MinIO
    2. Processed by GROBID for metadata extraction
    3. Split into chunks with embeddings for semantic search
    """
    # Map schema enum to model enum
    doc_type = DocumentType(type.value)
    
    async def progress_callback(progress: int, message: str):
        if client_id:
            await manager.send_personal_message(
                {"status": "processing", "progress": progress, "message": message},
                client_id
            )
    
    document = await process_document(
        file=file,
        db=db,
        document_type=doc_type,
        is_private=is_private,
        progress_callback=progress_callback
    )
    
    if client_id:
        await manager.send_personal_message(
            {"status": "complete", "progress": 100, "message": "Done"},
            client_id
        )
    
    # Get chunk count
    chunk_count = db.query(func.count(DocumentChunk.id)).filter(
        DocumentChunk.document_id == document.id
    ).scalar() or 0
    
    return _build_document_response(document, chunk_count)


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

