from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, extract, or_, case, literal
from fastapi import HTTPException
import re

from app.models.chat import Conversation, Chat, ChatReference, ChatRole
from app.models.document_chunk import DocumentChunk
from app.schemas.chat import ChatRequest, ChatResponse, ConversationResponse
from app.services.llm import generate_response
from app.services.embedding import generate_embedding
from app.models.document import Document, DocumentType

class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, user_id: int, title: str) -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversation(self, conversation_id: int, user_id: int) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()

    def list_conversations(self, user_id: int, limit: int = 20, offset: int = 0) -> List[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    def _handle_conversation(self, user_id: int, request: ChatRequest) -> Conversation:
        """Handle conversation creation or retrieval."""
        if request.conversation_id:
            conversation = self.get_conversation(request.conversation_id, user_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return conversation
        else:
            title = " ".join(request.message.split()[:5])
            return self.create_conversation(user_id, title)

    def _save_chat_message(self, conversation_id: int, role: ChatRole, message: str) -> Chat:
        """Save a chat message to the database."""
        chat_msg = Chat(
            conversation_id=conversation_id,
            role=role,
            message=message
        )
        self.db.add(chat_msg)
        self.db.commit()
        self.db.refresh(chat_msg)
        return chat_msg

    # =========================================================================
    # Query Processing
    # =========================================================================

    def _process_query(self, query: str) -> Dict[str, Any]:
        """
        Process user query: clean text and extract Dublin Core entities.
        
        Returns:
            {
                "cleaned_query": str,
                "entities": { "year": ..., "creator": ..., ... },
                "keywords": [str]
            }
        """
        # Step 1: Clean query
        cleaned = self._clean_query(query)
        
        # Step 2: Extract entities mapped to Dublin Core
        entities = self._extract_entities(query)
        
        # Step 3: Extract keywords (excluding entity values already captured)
        keywords = self._extract_keywords(cleaned, entities)
        
        result = {
            "original_query": query,
            "cleaned_query": cleaned,
            "entities": entities,
            "keywords": keywords
        }
        
        print("========== QUERY PROCESSING ==========")
        print(f"  Original : {query}")
        print(f"  Cleaned  : {cleaned}")
        print(f"  Entities : {entities}")
        print(f"  Keywords : {keywords}")
        print("=======================================")
        
        return result

    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query text."""
        # Lowercase
        cleaned = query.lower().strip()
        # Remove excessive punctuation but keep meaningful ones
        cleaned = re.sub(r'[?!.,;:]+$', '', cleaned)
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """
        Extract Dublin Core-mapped entities from query using regex patterns.
        
        Mappings:
            year        → Document.date
            creator     → Document.creator / Document.contributor
            language    → Document.language
            publisher   → Document.publisher
            location    → Document.coverage
            source      → Document.source (journal/conference)
            doi         → Document.doi
            doc_type    → Document.type
            topic       → used for semantic search (not a hard filter)
        """
        query_lower = query.lower()
        entities = {}
        
        # 1. Year (4-digit number 1900-2099)
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', query)
        if year_match:
            entities["year"] = int(year_match.group(1))
        
        # 2. Creator/Author - patterns: "oleh X", "penulis X", "author X", "ditulis oleh X"
        author_patterns = [
            r'(?:oleh|penulis|author|ditulis oleh|karya)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)',
            r'(?:oleh|penulis|author|ditulis oleh|karya)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,3})',
        ]
        for pattern in author_patterns:
            author_match = re.search(pattern, query, re.IGNORECASE)
            if author_match:
                author_name = author_match.group(1).strip()
                # Filter out stopwords that might be captured
                stopwords = {'dan', 'di', 'yang', 'untuk', 'dari', 'pada', 'tahun', 'tentang'}
                name_words = [w for w in author_name.split() if w.lower() not in stopwords]
                if name_words:
                    entities["creator"] = " ".join(name_words)
                break
        
        # 3. Language - patterns: "bahasa X", "berbahasa X", "dalam bahasa X"
        lang_patterns = {
            r'(?:bahasa|berbahasa|dalam bahasa)\s+(indonesia|inggris|english|indonesian|melayu|arab|jepang|mandarin)': {
                'indonesia': 'id', 'indonesian': 'id',
                'inggris': 'en', 'english': 'en',
                'melayu': 'ms', 'arab': 'ar', 'jepang': 'ja', 'mandarin': 'zh'
            }
        }
        for pattern, lang_map in lang_patterns.items():
            lang_match = re.search(pattern, query_lower)
            if lang_match:
                lang_name = lang_match.group(1)
                entities["language"] = lang_map.get(lang_name, lang_name)
                break
        
        # 4. Publisher - patterns: "diterbitkan X", "penerbit X", "published by X"
        publisher_match = re.search(
            r'(?:diterbitkan(?:\s+oleh)?|penerbit|published\s+by)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,4})',
            query, re.IGNORECASE
        )
        if publisher_match:
            entities["publisher"] = publisher_match.group(1).strip()
        
        # 5. Location/Coverage - patterns: "di X" (place names)
        location_match = re.search(
            r'\bdi\s+(Indonesia|Jawa|Sumatera|Kalimantan|Sulawesi|Bali|Papua|'
            r'Jakarta|Bandung|Surabaya|Medan|Yogyakarta|Semarang|Malang|'
            r'Asia|Eropa|Amerika|Afrika|Australia)\b',
            query, re.IGNORECASE
        )
        if location_match:
            entities["location"] = location_match.group(1)
        
        # 6. Source/Journal - patterns: "jurnal X", "journal X", "di jurnal X"
        journal_match = re.search(
            r'(?:jurnal|journal|majalah|di\s+jurnal|di\s+journal)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+){0,4})',
            query, re.IGNORECASE
        )
        if journal_match:
            entities["source"] = journal_match.group(1).strip()
        
        # 7. DOI pattern
        doi_match = re.search(r'(10\.\d{4,}/[^\s]+)', query)
        if doi_match:
            entities["doi"] = doi_match.group(1)
        
        # 8. Document type - patterns: specific keywords
        type_map = {
            r'\b(thesis|tesis|skripsi|disertasi)\b': DocumentType.THESIS,
            r'\b(conference|konferensi|seminar|prosiding)\b': DocumentType.CONFERENCE,
            r'\b(buku|book)\b': DocumentType.BOOK,
            r'\b(laporan|report)\b': DocumentType.REPORT,
            r'\b(jurnal|journal|artikel)\b': DocumentType.JOURNAL,
        }
        for pattern, doc_type in type_map.items():
            if re.search(pattern, query_lower):
                entities["doc_type"] = doc_type
                break
        
        return entities

    def _extract_keywords(self, cleaned_query: str, entities: Dict[str, Any] = None) -> List[str]:
        """Extract meaningful keywords from query, excluding already-extracted entity values."""
        stopwords = {
            'di', 'dan', 'yang', 'untuk', 'dengan', 'dari', 'ke', 'ini', 'itu',
            'adalah', 'pada', 'dalam', 'oleh', 'akan', 'atau', 'juga', 'sudah',
            'ada', 'bisa', 'dapat', 'saya', 'apa', 'bagaimana', 'mengapa', 'kapan',
            'tentang', 'mengenai', 'terkait', 'seputar', 'informasi', 'jelaskan',
            'hasil', 'penelitian', 'penulis', 'author', 'bahasa', 'berbahasa',
            'tahun', 'diterbitkan', 'penerbit', 'jurnal', 'journal', 'oleh',
            'karya', 'ditulis', 'published'
        }
        
        words = cleaned_query.split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Remove entity values from keywords to avoid duplication
        if entities:
            entity_words = set()
            for key, val in entities.items():
                if isinstance(val, str):
                    entity_words.update(val.lower().split())
                elif isinstance(val, int):
                    entity_words.add(str(val))
            keywords = [k for k in keywords if k not in entity_words]
        
        return keywords

    # =========================================================================
    # Metadata Filtering
    # =========================================================================

    def _build_metadata_filters(self, entities: Dict[str, Any]) -> List:
        """
        Build SQLAlchemy filter conditions from extracted entities.
        Maps entities to Dublin Core columns in Document table.
        """
        filters = []
        
        if not entities:
            return filters
        
        # Year → Document.date (extract year)
        if "year" in entities:
            filters.append(
                extract('year', Document.date) == entities["year"]
            )
        
        # Creator → Document.creator OR Document.contributor
        if "creator" in entities:
            creator_val = f"%{entities['creator']}%"
            filters.append(
                or_(
                    Document.creator.ilike(creator_val),
                    Document.contributor.ilike(creator_val)
                )
            )
        
        # Language → Document.language
        if "language" in entities:
            filters.append(
                Document.language.ilike(f"%{entities['language']}%")
            )
        
        # Publisher → Document.publisher
        if "publisher" in entities:
            filters.append(
                Document.publisher.ilike(f"%{entities['publisher']}%")
            )
        
        # Location → Document.coverage
        if "location" in entities:
            filters.append(
                Document.coverage.ilike(f"%{entities['location']}%")
            )
        
        # Source/Journal → Document.source
        if "source" in entities:
            filters.append(
                Document.source.ilike(f"%{entities['source']}%")
            )
        
        # DOI → Document.doi
        if "doi" in entities:
            filters.append(
                Document.doi == entities["doi"]
            )
        
        # Document type → Document.type
        if "doc_type" in entities:
            filters.append(
                Document.type == entities["doc_type"]
            )
        
        print(f"  Metadata filters: {len(filters)} applied")
        return filters

    # =========================================================================
    # Hybrid Search (Semantic + Keyword + Metadata)
    # =========================================================================

    def _calculate_keyword_score(self, content: str, doc: 'Document', keywords: List[str]) -> float:
        """
        Calculate keyword matching score (0.0 to 1.0) using all Dublin Core metadata.
        Searches in: title, creator, keywords, description, publisher, contributor, 
                     date, abstract, language, relation
        """
        if not keywords:
            return 0.0
        
        content_lower = content.lower()
        
        # Convert date to string for matching
        date_str = str(doc.date) if doc.date else ""
        
        # All Dublin Core metadata fields with weights
        metadata_fields = {
            'title': (doc.title.lower() if doc.title else "", 3),
            'keywords': (doc.keywords.lower() if doc.keywords else "", 2.5),
            'abstract': (doc.abstract.lower() if doc.abstract else "", 2),
            'description': (doc.description.lower() if doc.description else "", 1.5),
            'creator': (doc.creator.lower() if doc.creator else "", 1.5),
            'contributor': (doc.contributor.lower() if doc.contributor else "", 1.5),
            'publisher': (doc.publisher.lower() if doc.publisher else "", 1),
            'source': (doc.source.lower() if doc.source else "", 1),
            'relation': (doc.relation.lower() if doc.relation else "", 1),
            'language': (doc.language.lower() if doc.language else "", 0.5),
            'date': (date_str, 0.5),
        }
        
        total_score = 0
        max_possible = 0
        
        for keyword in keywords:
            keyword_matched = False
            
            for field_name, (field_value, weight) in metadata_fields.items():
                if keyword in field_value:
                    total_score += weight
                    keyword_matched = True
                    break
            
            if not keyword_matched and keyword in content_lower:
                total_score += 0.5
            
            max_possible += 3
        
        return min(total_score / max_possible, 1.0) if max_possible > 0 else 0.0

    def _retrieve_relevant_chunks(
        self, 
        query: str, 
        metadata_filters: List = None,
        limit: int = 5, 
        threshold: float = 0.55
    ) -> Tuple[List[DocumentChunk], List[float]]:
        """
        Retrieve relevant document chunks using hybrid search:
        1. Metadata filtering (Dublin Core pre-filter)
        2. Semantic similarity (embedding cosine distance)
        3. Keyword matching boost
        4. Document diversification (max chunks per document)
        """
        query_embedding = generate_embedding(query)
        
        if query_embedding is None:
            print("Warning: Failed to generate query embedding")
            return [], []
        
        MIN_CONTENT_LENGTH = 100
        MAX_CHUNKS_PER_DOCUMENT = 10
        
        keywords = self._extract_keywords(query)
        
        # Build base query with both content embedding and question embedding scores
        content_sim = (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label('semantic_score')
        
        # Question embedding similarity: use CASE to handle NULLs
        question_sim = case(
            (DocumentChunk.possibly_question_embedding.isnot(None),
             1 - DocumentChunk.possibly_question_embedding.cosine_distance(query_embedding)),
            else_=literal(0.0)
        ).label('question_score')
        
        base_query = self.db.query(
            DocumentChunk,
            Document,
            content_sim,
            question_sim
        ).join(
            Document, DocumentChunk.document_id == Document.id
        ).filter(
            # Exclude invalid titles
            Document.title.isnot(None),
            Document.title != "",
            Document.title != "Untitled Document",
            ~Document.title.ilike("untitled%"),
            # Exclude invalid content
            DocumentChunk.content.isnot(None),
            DocumentChunk.content != "",
            func.length(DocumentChunk.content) >= MIN_CONTENT_LENGTH,
            DocumentChunk.embedding.isnot(None)
        )

        print("========== BASE QUERY ==========")
        print(base_query)
        print("============================================")
        
        # Apply metadata filters from entity extraction
        has_metadata_filters = metadata_filters and len(metadata_filters) > 0
        
        print("========== METADATA FILTERS ==========")
        print(has_metadata_filters)
        print("============================================")

        if has_metadata_filters:
            filtered_query = base_query.filter(*metadata_filters)
            filtered_results = filtered_query.order_by(
                desc('semantic_score')
            ).limit(limit * 4).all()
            
            print(f"  Metadata-filtered results: {len(filtered_results)} chunks")
            
            # If filtered results are too few, fallback to unfiltered
            if len(filtered_results) >= 2:
                chunks_with_distance = filtered_results
            else:
                print("  Too few filtered results, falling back to unfiltered search")
                chunks_with_distance = base_query.order_by(
                    desc('semantic_score')
                ).limit(limit * 4).all()
        else:
            chunks_with_distance = base_query.order_by(
                desc('semantic_score')
            ).limit(limit * 4).all()
        
        # Re-rank with hybrid scoring (content + question + keyword)
        scored_chunks = []
        for chunk, doc, semantic_score, question_score in chunks_with_distance:
            if semantic_score is None:
                continue
            
            keyword_score = self._calculate_keyword_score(
                chunk.content, 
                doc,
                keywords
            )
            
            # Combined semantic score: best of content embedding and question embedding
            # question_score is 0.0 when possibly_question_embedding is NULL
            q_score = float(question_score) if question_score else 0.0
            combined_semantic = max(float(semantic_score), q_score)
            
            # Hybrid score: 70% combined semantic + 30% keyword
            if has_metadata_filters:
                hybrid_score = combined_semantic
            else:
                hybrid_score = combined_semantic
                
            # if has_metadata_filters:
            #     hybrid_score = (combined_semantic * 0.85) + (keyword_score * 0.15)
            # else:
            #     hybrid_score = (combined_semantic * 0.7) + (keyword_score * 0.3)
            
            # Bonus if document matched metadata filters
            if has_metadata_filters:
                hybrid_score *= 1.1  # 10% boost for metadata-matched docs

            print(f"  Chunk {chunk.id}: content_sim={float(semantic_score):.4f}, question_sim={q_score:.4f}, combined={combined_semantic:.4f}, keyword={keyword_score:.4f}, hybrid={hybrid_score:.4f}")
            
            scored_chunks.append({
                'chunk': chunk,
                'document_id': doc.id,
                'document_title': doc.title,
                'semantic_score': float(semantic_score),
                'question_score': q_score,
                'combined_semantic': combined_semantic,
                'keyword_score': keyword_score,
                'hybrid_score': hybrid_score
            })
        
        # Sort by hybrid score
        scored_chunks.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        # Apply document diversification and threshold
        chunks = []
        similarities = []
        doc_chunk_count = {}
        
        for item in scored_chunks:
            doc_id = item['document_id']
            hybrid_score = item['hybrid_score']
            
            if hybrid_score < threshold:
                continue
            
            if doc_chunk_count.get(doc_id, 0) >= MAX_CHUNKS_PER_DOCUMENT:
                continue
            
            chunks.append(item['chunk'])
            similarities.append(hybrid_score)
            doc_chunk_count[doc_id] = doc_chunk_count.get(doc_id, 0) + 1
            
            if len(chunks) >= limit:
                break
        
        return chunks, similarities

    # =========================================================================
    # Context & Prompt Construction
    # =========================================================================

    def _construct_context_text(self, chunks: List[DocumentChunk]) -> str:
        """Format chunks into a context string."""
        context_parts = []
        for chunk in chunks:
            doc = self.db.query(Document).filter(Document.id == chunk.document_id).first()
            doc_title = doc.title if doc else "Unknown Document"
            
            context_parts.append(
                f"[Source: {doc_title}]\n{chunk.content}"
            )
        return "\n\n---\n\n".join(context_parts) if context_parts else ""

    def _construct_rag_prompt(self, message: str, context_text: str) -> str:
        """Construct the prompt for the LLM."""
        if context_text:
            system_prompt = """Anda adalah asisten AI yang menjawab pertanyaan berdasarkan dokumen knowledge base.

INSTRUKSI:
1. Gunakan informasi dari KONTEKS di bawah untuk menjawab pertanyaan user.
2. Jawab dengan lengkap dan informatif menggunakan data yang ada di konteks.
3. Jika konteks membahas topik yang relevan, berikan jawaban terbaik berdasarkan informasi tersebut.
4. Sebutkan sumber dokumen ([Source: ...]) dalam jawaban Anda.
5. Gunakan bahasa yang sama dengan pertanyaan user.
6. Jika konteks benar-benar TIDAK MEMBAHAS topik pertanyaan sama sekali, katakan bahwa informasi tidak ditemukan."""

            return f"""{system_prompt}

KONTEKS DARI DOKUMEN:
{context_text}

---

PERTANYAAN USER: {message}

JAWABAN (berdasarkan konteks di atas):"""
        else:
            no_context_msg = "Maaf, saya tidak menemukan informasi yang relevan dengan pertanyaan Anda dalam dokumen yang tersedia."
            return f"""Anda adalah asisten AI berbasis dokumen knowledge base.

Tidak ditemukan dokumen yang relevan di knowledge base untuk pertanyaan ini.

PERTANYAAN USER: {message}

Jawab dengan: {no_context_msg}"""

    # =========================================================================
    # References
    # =========================================================================

    def _save_rag_references(self, bot_chat_id: int, chunks: List[DocumentChunk], similarities: List[float]):
        """Save references for the RAG response."""
        for i, chunk in enumerate(chunks):
            reference = ChatReference(
                chat_id=bot_chat_id,
                document_id=chunk.document_id,
                chunk_id=chunk.id,
                relevance_score=float(similarities[i]),
                quote=chunk.content[:200],
                page_number=chunk.page_number
            )
            self.db.add(reference)
        self.db.commit()

    # =========================================================================
    # Main Chat Processing
    # =========================================================================

    async def process_chat(self, user_id: int, request: ChatRequest) -> ChatResponse:
        # 1. Handle Conversation
        conversation = self._handle_conversation(user_id, request)
        
        # 2. Save User Message
        self._save_chat_message(conversation.id, ChatRole.USER, request.message)

        # 3. Query Processing: clean + extract entities
        query_info = self._process_query(request.message)
        print("========== QUERY INFO ==========")
        print(query_info)
        print("============================================")
        
        # 4. Build metadata filters from extracted entities
        metadata_filters = self._build_metadata_filters(query_info["entities"])
        print("========== METADATA FILTERS ==========")
        print(metadata_filters)
        print("============================================")
        # 5. RAG: Retrieve Context (with metadata filtering)
        chunks, similarities = self._retrieve_relevant_chunks(
            query=query_info["cleaned_query"],
            metadata_filters=metadata_filters
        )
        print("========== SIMILARITIES ==========")
        print(similarities)
        print("============================================")
        
        # 5b. Relevance Validation - reject low-quality results
        if chunks and similarities:
            avg_score = sum(similarities) / len(similarities)
            print(f"  Average similarity: {avg_score:.4f} (min threshold: 0.5)")
            if avg_score < 0.5:
                print("  WARNING: Retrieved context has low relevance, discarding")
                chunks = []
                similarities = []
                print("========== similarities after discard ==========")
                print(similarities)
                print("============================================")
        
        context_text = self._construct_context_text(chunks)
        
        # 6. Construct Prompt
        full_prompt = self._construct_rag_prompt(request.message, context_text)
        print("========== FULL PROMPT ==========")
        print(full_prompt[:2000])
        print("============================================")
        # 7. Generate Response
        answer = await generate_response(full_prompt)

        # Print RAGAS evaluation data
        retrieved_docs = [chunk.content for chunk in chunks]
        ragas_data = {
            "query": [request.message],
            "generated_response": [answer],
            "retrieved_documents": [retrieved_docs]
        }
        print("========== RAGAS EVALUATION DATA ==========")
        print(ragas_data)
        print("============================================")

        # 8. Save Bot Message
        bot_chat = self._save_chat_message(conversation.id, ChatRole.BOT, answer)

        # 9. Save References
        self._save_rag_references(bot_chat.id, chunks, similarities)

        return ChatResponse(
            id=bot_chat.id,
            conversation_id=conversation.id,
            role=bot_chat.role,
            message=bot_chat.message,
            created_at=bot_chat.created_at,
            references=[]
        )
