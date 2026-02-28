"""LLM-based metadata extraction service using Google Gemini."""
import json
import re
from typing import Dict, Any, Optional
from app.services.llm import generate_response


async def extract_metadata_with_llm(fulltext: str, existing_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extract document metadata using Google Gemini LLM.
    
    Args:
        fulltext: The full text content of the document
        existing_metadata: Optional existing metadata to fill in missing fields
    
    Returns:
        Dictionary with extracted metadata fields
    """
    if not fulltext or len(fulltext.strip()) < 100:
        print("Warning: Fulltext too short for LLM metadata extraction")
        return {}

    # Truncate fulltext if too long (keep first 8000 chars for context)
    text_sample = fulltext[:8000] if len(fulltext) > 8000 else fulltext
    
    # Build prompt
    prompt = _build_extraction_prompt(text_sample, existing_metadata)
    
    try:
        response_text = await generate_response(prompt)
        
        # Parse JSON from response
        extracted = _parse_llm_response(response_text)
        
        print(f"LLM extracted metadata: {list(extracted.keys())}")
        return extracted
        
    except Exception as e:
        print(f"LLM metadata extraction error: {str(e)}")
        return {}


def _build_extraction_prompt(text_sample: str, existing_metadata: Dict[str, Any] = None) -> str:
    """Build the prompt for metadata extraction."""
    
    all_fields = [
        "title", "abstract", "keywords", "creator", "contributor",
        "publisher", "language", "description", "date", "source", "coverage"
    ]
    
    missing_fields = []
    if existing_metadata:
        for field in all_fields:
            value = existing_metadata.get(field)
            if field == "title":
                if not value or value.strip() == "" or "untitled" in str(value).lower():
                    missing_fields.append(field)
            elif not value or (isinstance(value, str) and value.strip() == ""):
                missing_fields.append(field)
    else:
        missing_fields = all_fields
    
    print(f'  Missing fields for LLM: {missing_fields}')
    
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

INSTRUKSI WAJIB:
1. Untuk "title": WAJIB ditemukan. Judul biasanya ada di awal dokumen, sebelum abstrak. 
   Jika tidak jelas tertulis, buatlah judul deskriptif berdasarkan topik utama dokumen.
   JANGAN pernah mengembalikan null atau kosong untuk title.
2. Untuk "abstract": Ekstrak ringkasan/abstrak dokumen
3. Untuk "keywords": Ekstrak kata kunci utama, pisahkan dengan koma. 
   Jika tidak ada, buat 3-5 kata kunci berdasarkan topik dokumen.
4. Untuk "creator": Nama penulis utama (author pertama)
5. Untuk "contributor": Nama penulis lain selain penulis utama, pisahkan dengan koma
6. Untuk "publisher": Nama penerbit, jurnal, atau institusi yang menerbitkan
7. Untuk "language": Bahasa utama dokumen ("id" untuk Indonesia, "en" untuk Inggris)
8. Untuk "description": Buat ringkasan 1-2 kalimat tentang isi dokumen
9. Untuk "date": Tanggal publikasi dalam format YYYY-MM-DD atau YYYY
10. Untuk "source": Nama jurnal, konferensi, atau sumber publikasi
11. Untuk "coverage": Cakupan geografis/temporal penelitian jika disebutkan

ATURAN PENTING:
- Jawab HANYA dalam format JSON yang valid
- Untuk field "title" dan "keywords": WAJIB diisi, TIDAK BOLEH null
- Untuk field lain: jika tidak ditemukan, gunakan null
- Jangan mengarang informasi yang tidak ada, KECUALI untuk title dan keywords

FORMAT RESPONSE (JSON ONLY):
{{
    "title": "judul dokumen (WAJIB ADA)",
    "abstract": "...",
    "keywords": "keyword1, keyword2, keyword3 (WAJIB ADA)",
    "creator": "...",
    "contributor": "...",
    "publisher": "...",
    "language": "...",
    "description": "...",
    "date": "...",
    "source": "...",
    "coverage": "..."
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
            if not value or value.strip() == "" or value.strip().lower() in ["untitled", "untitled document"]:
                print(f"  Field '{field}' is missing or default: {value}")
                return True
        elif not value or (isinstance(value, str) and value.strip() == ""):
            print(f"  Field '{field}' is missing: {value}")
            return True
    
    # Also check important secondary fields
    secondary_fields = ["description", "publisher", "language"]
    missing_secondary = 0
    for field in secondary_fields:
        value = metadata.get(field)
        if not value or (isinstance(value, str) and value.strip() == ""):
            missing_secondary += 1
    
    if missing_secondary >= 2:
        print(f"  {missing_secondary} secondary fields missing, triggering LLM fallback")
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
        
        is_empty = (
            existing_value is None or
            (isinstance(existing_value, str) and existing_value.strip() == "")
        )
        
        is_default_title = (
            key == "title" and 
            existing_value and 
            str(existing_value).strip().lower() in ["untitled", "untitled document"]
        )
        
        if is_empty or is_default_title:
            merged[key] = llm_value
            print(f"  LLM filled missing field '{key}': {str(llm_value)[:80]}")
    
    return merged
