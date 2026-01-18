from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth
from app.api.routes import documents
from app.database import engine, Base
from app.services.minio import get_minio_client, ensure_bucket_exists
from app.services.document import ensure_documents_bucket_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create database tables and ensure MinIO buckets exist
    Base.metadata.create_all(bind=engine)
    
    # Ensure MinIO buckets exist
    try:
        client = get_minio_client()
        ensure_bucket_exists(client)
        ensure_documents_bucket_exists(client)
        print("✓ MinIO buckets ready")
    except Exception as e:
        print(f"⚠ MinIO connection warning: {e}")
    
    yield
    
    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="RAG Journal Chatbot API",
    description="FastAPI backend for scientific journal storage and RAG-based chatbot using GROBID, MinIO, PostgreSQL/pgvector, and Ollama",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(documents.router)


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "API is running"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "version": "1.0.0"
    }
