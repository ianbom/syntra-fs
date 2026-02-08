"""LLM-based metadata extraction service using Google Gemini."""
import json
import re
from typing import Dict, Any, Optional
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()


async def extract_metadata_with_llm(fulltext: str, existing_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extract document metadata using Google Gemini LLM.
    
    Args:
        fulltext: The full text content of the document
        existing_metadata: Optional existing metadata to fill in missing fields
    
    Returns:
        Dictionary with extracted metadata fields
    """
    api_key = settings.GOOGLE_API_KEY or settings.GEMINI_API_KEY
    if not api_key:
        print("Warning: Google API key not configured for LLM metadata extraction")
        return {}
    
    if not fulltext or len(fulltext.strip()) < 100:
        print("Warning: Fulltext too short for LLM metadata extraction")
        return {}
    
    # Truncate fulltext if too long (keep first 8000 chars for context)
    text_sample = fulltext[:8000] if len(fulltext) > 8000 else fulltext
    
    # Build prompt
    prompt = _build_extraction_prompt(text_sample, existing_metadata)
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(settings.GOOGLE_GENERATION_MODEL)
        
        response = await model.generate_content_async(prompt)
        
        # Parse JSON from response
        extracted = _parse_llm_response(response.text)
        
        print(f"LLM extracted metadata: {list(extracted.keys())}")
        return extracted
        
    except Exception as e:
        print(f"LLM metadata extraction error: {str(e)}")
        return {}


def _build_extraction_prompt(text_sample: str, existing_metadata: Dict[str, Any] = None) -> str:
    """Build the prompt for metadata extraction."""
    
    missing_fields = []
    if existing_metadata:
        field_checks = [
            ("title", existing_metadata.get("title") in [None, "", "Untitled Document"]),
            ("abstract", not existing_metadata.get("abstract")),
            ("keywords", not existing_metadata.get("keywords")),
            ("creator", not existing_metadata.get("creator")),
            ("publisher", not existing_metadata.get("publisher")),
            ("language", not existing_metadata.get("language")),
            ("description", not existing_metadata.get("description")),
        ]
        missing_fields = [field for field, is_missing in field_checks if is_missing]
    else:
        missing_fields = ["title", "abstract", "keywords", "creator", "publisher", "language", "description"]
    print('===========missing field========')
    print(missing_fields)
    if not missing_fields:
        return ""
    
    fields_instruction = ", ".join(missing_fields)
    
    prompt = f"""Anda adalah asisten yang mengekstrak metadata dari dokumen akademik/ilmiah.

TEKS DOKUMEN:
\"\"\"
{text_sample}
\"\"\"

TUGAS:
Ekstrak metadata berikut dari dokumen di atas: {fields_instruction}

INSTRUKSI:
1. Untuk "title": Ekstrak judul lengkap dokumen (biasanya di awal dokumen)
2. Untuk "abstract": Ekstrak ringkasan/abstrak dokumen (biasanya setelah judul)
3. Untuk "keywords": Ekstrak kata kunci utama, pisahkan dengan koma
4. Untuk "creator": Ekstrak nama penulis utama (author pertama)
5. Untuk "publisher": Ekstrak nama penerbit atau jurnal
6. Untuk "language": Tentukan bahasa dokumen (contoh: "en", "id")
7. Untuk "description": Buat ringkasan singkat 1-2 kalimat tentang dokumen

PENTING:
- Jawab HANYA dalam format JSON yang valid
- Jika tidak bisa menemukan informasi untuk suatu field, gunakan null
- Jangan mengarang informasi yang tidak ada dalam dokumen

FORMAT RESPONSE (JSON ONLY):
{{
    "title": "...",
    "abstract": "...",
    "keywords": "...",
    "creator": "...",
    "publisher": "...",
    "language": "...",
    "description": "..."
}}"""

    return prompt


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response."""
    try:
        # Try direct JSON parse
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find JSON object in response
    json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    print(f"Warning: Could not parse LLM response as JSON: {response_text[:200]}")
    return {}


def is_metadata_incomplete(metadata: Dict[str, Any]) -> bool:
    """Check if metadata has critical missing fields."""
    critical_fields = ["title", "abstract", "keywords", "creator"]
    
    for field in critical_fields:
        value = metadata.get(field)
        if field == "title":
            # Title is considered missing if None, empty, or contains "Untitled"
            if not value or value.strip() == "" or "untitled" in str(value).lower():
                print(f"  Field '{field}' is missing or default: {value}")
                return True
        elif not value or (isinstance(value, str) and value.strip() == ""):
            print(f"  Field '{field}' is missing: {value}")
            return True
    
    return False


def merge_metadata(grobid_metadata: Dict[str, Any], llm_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge GROBID and LLM metadata, preferring non-empty values.
    GROBID values take precedence unless they are empty/null.
    """
    merged = grobid_metadata.copy()
    
    for key, llm_value in llm_metadata.items():
        if llm_value is None or (isinstance(llm_value, str) and llm_value.strip() == ""):
            continue
            
        existing_value = merged.get(key)
        
        # Check if existing value is empty/null/default
        is_empty = (
            existing_value is None or
            (isinstance(existing_value, str) and existing_value.strip() == "")
        )
        
        is_default_title = (
            key == "title" and 
            existing_value and 
            "untitled" in str(existing_value).lower()
        )
        
        if is_empty or is_default_title:
            merged[key] = llm_value
            print(f"  LLM filled missing field '{key}': {llm_value[:50] if len(str(llm_value)) > 50 else llm_value}")
    
    return merged
