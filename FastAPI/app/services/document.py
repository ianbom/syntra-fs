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
from app.services.grobid import extract_header, extract_fulltext, extract_references, format_for_database, extract_structured_fulltext
from app.services.embedding import generate_embedding
from app.services.minio import get_minio_client
from app.services.question_generator import generate_possibly_questions
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

# Smart chunking constants
MIN_CHUNK_WORDS = 80       # Merge paragraphs shorter than this
MAX_CHUNK_WORDS = 800      # Split paragraphs longer than this
IDEAL_CHUNK_WORDS = 400    # Target chunk size for splitting
KEYWORDS_PER_CHUNK = 7     # Number of keywords to extract per chunk

# Indonesian + English stopwords for keyword extraction
_STOPWORDS = frozenset({
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "about", "up",
    "that", "this", "these", "those", "it", "its", "he", "she", "they",
    "we", "you", "i", "me", "him", "her", "us", "them", "my", "your",
    "his", "our", "their", "what", "which", "who", "whom", "also", "et",
    "al", "etc", "fig", "figure", "table", "using", "based", "however",
    "therefore", "thus", "hence", "since", "although", "though", "yet",
    "still", "already", "even", "well", "back", "also", "much", "any",
    # Indonesian
    "dan", "atau", "yang", "di", "ke", "dari", "pada", "untuk", "dengan",
    "adalah", "ini", "itu", "akan", "oleh", "telah", "sudah", "belum",
    "tidak", "bukan", "dapat", "bisa", "harus", "juga", "serta", "dalam",
    "antara", "melalui", "karena", "jika", "bila", "agar", "supaya",
    "tetapi", "namun", "selain", "meskipun", "walaupun", "bahwa", "hal",
    "lebih", "sangat", "saat", "ketika", "setelah", "sebelum", "secara",
    "seperti", "sebagai", "tersebut", "mereka", "kami", "kita", "saya",
    "yaitu", "yakni", "maupun", "adapun", "sedangkan", "maka", "pun",
})


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
# Text Chunking (Legacy - kept for backward compatibility)
# =============================================================================

class TextChunker:
    """Handles text chunking with metadata (legacy fixed-size approach)."""
    
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
# Smart Chunking (Section & Paragraph-aware)
# =============================================================================

import re as _re


class SmartChunker:
    """
    Smart chunking strategy that respects document structure.
    
    Instead of splitting by fixed word count, this chunker:
    1. Uses GROBID's structured sections (title, abstract, body sections, references)
    2. Chunks by paragraph boundaries within each section
    3. Merges short paragraphs with the next one to avoid tiny chunks
    4. Splits overly long paragraphs at sentence boundaries
    5. Preserves section metadata for each chunk
    6. Extracts keywords per-chunk and resolves accurate page numbers
    7. Guarantees NO text is lost — every character from the document is included
    """
    
    def __init__(
        self,
        min_chunk_words: int = MIN_CHUNK_WORDS,
        max_chunk_words: int = MAX_CHUNK_WORDS,
        ideal_chunk_words: int = IDEAL_CHUNK_WORDS,
    ):
        self.min_chunk_words = min_chunk_words
        self.max_chunk_words = max_chunk_words
        self.ideal_chunk_words = ideal_chunk_words
    
    def chunk_structured_sections(
        self,
        sections: List[Dict[str, Any]],
        document_title: str = None,
        pages_data: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Smart-chunk a list of structured sections from GROBID.
        
        Args:
            sections: Output of extract_structured_fulltext()
            document_title: Title of the document (for metadata)
            pages_data: Per-page text from PyMuPDF [{"page_number": int, "text": str}]
        
        Returns:
            List of chunk dicts ready for embedding + DB storage.
        """
        all_chunks: List[Dict[str, Any]] = []
        
        for section in sections:
            sec_type = section.get("type", "section")
            sec_title = section.get("title", "")
            paragraphs = section.get("paragraphs", [])
            
            if not paragraphs:
                # Fallback: use content directly
                content = section.get("content", "").strip()
                if content:
                    paragraphs = [content]
                else:
                    continue
            
            # Map section type to ChunkType
            chunk_type = self._map_chunk_type(sec_type)
            
            # Process paragraphs for this section
            section_chunks = self._process_section_paragraphs(
                paragraphs=paragraphs,
                section_title=sec_title,
                chunk_type=chunk_type,
                document_title=document_title,
            )
            all_chunks.extend(section_chunks)
        
        # Re-index all chunks sequentially
        for i, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = i
        
        # Enrich chunks: resolve page numbers + extract keywords
        for chunk in all_chunks:
            # Resolve accurate page number from PyMuPDF page data
            if pages_data:
                resolved_page = self._find_page_number(chunk["content"], pages_data)
                if resolved_page is not None:
                    chunk["page_number"] = resolved_page
                    chunk["chunk_metadata"]["page_number"] = resolved_page
            
            # Extract keywords for this chunk
            keywords = self._extract_keywords(chunk["content"])
            chunk["chunk_metadata"]["keywords"] = keywords
        
        # Validate: count total characters to ensure nothing is lost
        input_chars = sum(
            len(" ".join(s.get("paragraphs", []))) for s in sections
        )
        output_chars = sum(len(c["content"]) for c in all_chunks)
        print(f"SmartChunker: {len(sections)} sections -> {len(all_chunks)} chunks")
        print(f"SmartChunker: Input chars={input_chars}, Output chars={output_chars}")
        
        return all_chunks
    
    def _process_section_paragraphs(
        self,
        paragraphs: List[str],
        section_title: str,
        chunk_type: ChunkType,
        document_title: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Process paragraphs within a section:
        - Merge short paragraphs together
        - Split long paragraphs at sentence boundaries
        """
        chunks = []
        buffer = ""  # Accumulator for merging short paragraphs
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            word_count = len(paragraph.split())
            buffer_word_count = len(buffer.split()) if buffer else 0
            
            if buffer:
                combined_word_count = buffer_word_count + word_count
                
                if combined_word_count <= self.max_chunk_words:
                    # Merge: combined is still within max limit
                    buffer = buffer + "\n\n" + paragraph
                else:
                    # Buffer is big enough, flush it as a chunk
                    chunks.extend(self._create_chunks_from_text(
                        text=buffer,
                        section_title=section_title,
                        chunk_type=chunk_type,
                        document_title=document_title,
                    ))
                    buffer = paragraph
            else:
                # Buffer is empty, start accumulating
                if word_count < self.min_chunk_words:
                    # Too short — start buffering for merging
                    buffer = paragraph
                else:
                    # Long enough on its own
                    if word_count > self.max_chunk_words:
                        # Too long — split at sentence boundaries
                        chunks.extend(self._create_chunks_from_text(
                            text=paragraph,
                            section_title=section_title,
                            chunk_type=chunk_type,
                            document_title=document_title,
                        ))
                    else:
                        # Just right — use as-is
                        buffer = paragraph
                        # Check if this paragraph is >= min, keep in buffer
                        # to potentially merge with next short paragraph
                        if word_count >= self.min_chunk_words:
                            # Flush if it's a reasonable size
                            chunks.extend(self._create_chunks_from_text(
                                text=buffer,
                                section_title=section_title,
                                chunk_type=chunk_type,
                                document_title=document_title,
                            ))
                            buffer = ""
        
        # Flush remaining buffer
        if buffer.strip():
            chunks.extend(self._create_chunks_from_text(
                text=buffer,
                section_title=section_title,
                chunk_type=chunk_type,
                document_title=document_title,
            ))
        
        return chunks
    
    def _create_chunks_from_text(
        self,
        text: str,
        section_title: str,
        chunk_type: ChunkType,
        document_title: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Create one or more chunks from a text block.
        If text exceeds max_chunk_words, split at sentence boundaries.
        """
        text = text.strip()
        if not text:
            return []
        
        word_count = len(text.split())
        
        if word_count <= self.max_chunk_words:
            # Fits in a single chunk
            return [self._build_chunk_dict(
                content=text,
                section_title=section_title,
                chunk_type=chunk_type,
                document_title=document_title,
            )]
        
        # Split at sentence boundaries
        sentences = self._split_into_sentences(text)
        chunks = []
        current_sentences = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            if current_word_count + sentence_words > self.max_chunk_words and current_sentences:
                # Flush current chunk
                chunk_text = " ".join(current_sentences)
                chunks.append(self._build_chunk_dict(
                    content=chunk_text,
                    section_title=section_title,
                    chunk_type=chunk_type,
                    document_title=document_title,
                ))
                current_sentences = []
                current_word_count = 0
            
            current_sentences.append(sentence)
            current_word_count += sentence_words
        
        # Flush remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            # If this remainder is too short and we have previous chunks, 
            # merge with the last chunk if it won't exceed max
            if (
                chunks 
                and current_word_count < self.min_chunk_words
                and len(chunks[-1]["content"].split()) + current_word_count <= self.max_chunk_words
            ):
                chunks[-1]["content"] += " " + chunk_text
                chunks[-1]["token_count"] = len(chunks[-1]["content"].split())
            else:
                chunks.append(self._build_chunk_dict(
                    content=chunk_text,
                    section_title=section_title,
                    chunk_type=chunk_type,
                    document_title=document_title,
                ))
        
        return chunks
    
    def _build_chunk_dict(
        self,
        content: str,
        section_title: str,
        chunk_type: ChunkType,
        document_title: str = None,
    ) -> Dict[str, Any]:
        """Build a single chunk dictionary with metadata."""
        words = content.split()
        word_count = len(words)
        # Estimate page number from cumulative word position
        estimated_page = max(1, (word_count // WORDS_PER_PAGE) + 1)
        
        return {
            "chunk_index": 0,  # Will be re-indexed later
            "content": content,
            "token_count": word_count,
            "chunk_type": chunk_type,
            "page_number": estimated_page,
            "section_title": section_title,
            "chunk_metadata": {
                "source_document": document_title,
                "section": section_title,
                "chunk_strategy": "smart",
                "word_count": word_count,
            }
        }
    
    @staticmethod
    def _map_chunk_type(section_type: str) -> ChunkType:
        """Map GROBID section type to ChunkType enum."""
        mapping = {
            "title": ChunkType.TITLE,
            "abstract": ChunkType.ABSTRACT,
            "reference": ChunkType.REFERENCE,
            "authors": ChunkType.PARAGRAPH,
            "keywords": ChunkType.PARAGRAPH,
            "section": ChunkType.PARAGRAPH,
        }
        return mapping.get(section_type, ChunkType.PARAGRAPH)
    
    @staticmethod
    def _split_into_sentences(text: str) -> List[str]:
        """
        Split text into sentences using regex.
        Handles common abbreviations and decimal numbers.
        """
        # Split on sentence-ending punctuation followed by space + uppercase,
        # or newlines that look like paragraph breaks
        sentence_endings = _re.compile(
            r'(?<=[.!?])\s+(?=[A-Z\u00C0-\u024F])|\n{2,}'
        )
        raw = sentence_endings.split(text)
        # Filter empty and strip
        return [s.strip() for s in raw if s and s.strip()]
    
    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = KEYWORDS_PER_CHUNK) -> List[str]:
        """
        Extract significant keywords from chunk content.
        Uses word frequency with stopword filtering.
        Returns a list of the most relevant keywords.
        """
        if not text or len(text.strip()) < 10:
            return []
        
        # Tokenize: lowercase, keep only alphabetic words of length >= 3
        words = _re.findall(r'[a-zA-Z\u00C0-\u024F]{3,}', text.lower())
        
        # Filter stopwords
        meaningful = [w for w in words if w not in _STOPWORDS and len(w) >= 3]
        
        if not meaningful:
            return []
        
        # Count frequency
        freq: Dict[str, int] = {}
        for w in meaningful:
            freq[w] = freq.get(w, 0) + 1
        
        # Sort by frequency descending, then alphabetically for ties
        sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
        
        # Return top keywords
        return [word for word, _ in sorted_words[:max_keywords]]
    
    @staticmethod
    def _find_page_number(
        chunk_content: str,
        pages_data: List[Dict[str, Any]],
    ) -> Optional[int]:
        """
        Find the actual PDF page number where the chunk content appears.
        Matches by searching for a snippet of the chunk content in each page's text.
        Returns 1-based page number, or None if not found.
        """
        if not chunk_content or not pages_data:
            return None
        
        # Take a representative snippet from the chunk (first ~120 chars)
        # Clean whitespace for better matching
        snippet = " ".join(chunk_content.split()[:20])  # first ~20 words
        if len(snippet) < 10:
            return None
        
        # Normalize for matching
        snippet_normalized = snippet.lower().strip()
        
        for page in pages_data:
            page_text_normalized = " ".join(page["text"].split()).lower()
            if snippet_normalized in page_text_normalized:
                return page["page_number"]
        
        # Fallback: try with a shorter snippet (first 10 words)
        short_snippet = " ".join(chunk_content.split()[:10]).lower().strip()
        if len(short_snippet) >= 10:
            for page in pages_data:
                page_text_normalized = " ".join(page["text"].split()).lower()
                if short_snippet in page_text_normalized:
                    return page["page_number"]
        
        return None


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
            coverage=metadata.get("coverage"),
            rights=metadata.get("rights"),
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
        """Generate embeddings, hypothetical questions, and save chunks to database."""
        total_chunks = len(chunks)
        
        for i, chunk_data in enumerate(chunks):
            # Progress update
            if progress_callback and i % 5 == 0:
                percent = 60 + int((i / total_chunks) * 30)
                await progress_callback(percent, f"Processing chunk {i+1}/{total_chunks} (embedding + questions)...")
            
            content = chunk_data["content"]
            
            # Generate content embedding
            embedding = generate_embedding(content)
            
            # Generate hypothetical questions from chunk content
            possibly_questions = None
            possibly_question_embedding = None
            try:
                section_title = chunk_data.get("section_title")
                doc_title = chunk_data.get("chunk_metadata", {}).get("source_document")
                questions = await generate_possibly_questions(
                    chunk_content=content,
                    section_title=section_title,
                    document_title=doc_title,
                )
                if questions:
                    possibly_questions = questions
                    # Combine questions into a single text and generate embedding
                    combined_questions = " ".join(questions)
                    possibly_question_embedding = generate_embedding(combined_questions)
            except Exception as e:
                print(f"  Warning: question generation failed for chunk {i}: {e}")
            
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
            self.db.add(chunk)


# =============================================================================
# Main Document Service
# =============================================================================

class DocumentService:
    """Main service for document processing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.storage = MinIOStorage()
        self.chunker = TextChunker()           # Legacy fallback
        self.smart_chunker = SmartChunker()     # Primary: smart chunking
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
        header = await extract_header(file_content)
        references = extract_references(file_content)
        fulltext = extract_fulltext(file_content)
        
        # Step 1b: Extract structured sections for smart chunking
        structured_sections = []
        try:
            if progress_callback:
                await progress_callback(35, "Extracting document structure for smart chunking...")
            structured_sections = extract_structured_fulltext(file_content)
            print(f"Extracted {len(structured_sections)} structured sections for smart chunking")
        except Exception as e:
            print(f"Structured extraction failed, will use legacy chunking: {e}")
        
        metadata = format_for_database(header, references)
        metadata["fulltext"] = fulltext or ""
        metadata["structured_sections"] = structured_sections
        
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
        Also populates self._pages_data for page-number resolution.
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
            self._pages_data = []  # Per-page data for page-number resolution
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if text and text.strip():
                    pages_text.append(text.strip())
                    self._pages_data.append({
                        "page_number": page_num + 1,  # 1-based
                        "text": text.strip()
                    })
            
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
        """
        Prepare all chunks using smart chunking (paragraph/section-aware).
        Falls back to legacy fixed-size chunking if structured extraction failed.
        
        Smart chunking ensures:
        - Chunks respect paragraph and section boundaries
        - Short paragraphs are merged with the next one
        - Long paragraphs are split at sentence boundaries
        - ALL text from the document is preserved (no text loss)
        """
        structured_sections = metadata.get("structured_sections", [])
        
        if structured_sections:
            # === PRIMARY: Smart chunking from structured sections ===
            print("Using SMART CHUNKING (section & paragraph-aware)")
            pages_data = getattr(self, '_pages_data', None)
            chunks = self.smart_chunker.chunk_structured_sections(
                sections=structured_sections,
                document_title=metadata.get("title"),
                pages_data=pages_data,
            )
            
            if chunks:
                print(f"Smart chunking produced {len(chunks)} chunks")
                return chunks
            else:
                print("Smart chunking produced 0 chunks, falling back to legacy")
        
        # === FALLBACK: Legacy fixed-size chunking ===
        print("Using LEGACY CHUNKING (fixed word-count)")
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
