"""Service for generating hypothetical questions from chunk content using LLM."""
import json
import re
from typing import List, Optional
from app.services.llm import generate_response


async def generate_possibly_questions(
    chunk_content: str,
    section_title: str = None,
    document_title: str = None,
    num_questions: int = 5,
) -> List[str]:
    """
    Generate hypothetical questions that could be answered by the given chunk content.

    Uses Google Gemini to produce questions that are contextually relevant
    to the chunk's content, section, and parent document.

    Args:
        chunk_content: The text content of the chunk.
        section_title: Optional section heading the chunk belongs to.
        document_title: Optional title of the parent document.
        num_questions: Number of questions to generate (default 5).

    Returns:
        List of question strings. Empty list on failure.
    """
    if not chunk_content or len(chunk_content.strip()) < 30:
        return []

    # Truncate very long chunks to stay within token limits
    text_sample = chunk_content[:4000] if len(chunk_content) > 4000 else chunk_content

    prompt = _build_question_prompt(
        text_sample,
        section_title=section_title,
        document_title=document_title,
        num_questions=num_questions,
    )

    try:
        response_text = await generate_response(prompt)
        questions = _parse_questions_response(response_text)

        if questions:
            print(f"  Generated {len(questions)} questions for chunk")
        return questions

    except Exception as e:
        print(f"Question generation error: {str(e)}")
        return []


def _build_question_prompt(
    text: str,
    section_title: str = None,
    document_title: str = None,
    num_questions: int = 5,
) -> str:
    """Build the LLM prompt for question generation."""

    context_info = ""
    if document_title:
        context_info += f"Dokumen: {document_title}\n"
    if section_title:
        context_info += f"Bagian: {section_title}\n"

    return f"""Anda adalah asisten yang membuat pertanyaan hipotetis dari potongan teks dokumen akademik.
Pertanyaan ini akan digunakan untuk PENCARIAN SEMANTIK (embedding-based retrieval), sehingga kualitas kata-kata dalam pertanyaan sangat penting.

{context_info}
TEKS:
\"\"\"
{text}
\"\"\"

TUGAS:
Buatlah {num_questions} pertanyaan yang bisa dijawab oleh teks di atas.

ATURAN:
1. Pertanyaan harus SPESIFIK dan berhubungan langsung dengan isi teks
2. Pertanyaan harus bervariasi (apa, bagaimana, mengapa, siapa, kapan, dll.)
3. Setiap pertanyaan harus bisa dijawab HANYA berdasarkan informasi di teks
4. Gunakan bahasa yang sama dengan teks (Indonesia atau Inggris)
5. Jangan membuat pertanyaan yang terlalu umum atau tidak relevan
6. Pertanyaan harus natural — seperti pertanyaan yang akan diajukan oleh pembaca
7. SANGAT PENTING: JANGAN gunakan kata ganti atau referensi umum seperti "ini", "tersebut", "paper ini", "penelitian ini", "dokumen ini", "studi ini", "teks ini". Selalu gunakan istilah SPESIFIK dari teks. Contoh:
   - BURUK: "Siapa authors dalam penelitian ini?"
   - BAIK: "Siapa authors dalam penelitian Produktivitas Padi di Blitar?"
   - BURUK: "Apa hasil dari studi ini?"
   - BAIK: "Apa hasil dari studi analisis dampak perubahan iklim terhadap pertanian?"
   Alasan: pertanyaan dengan kata ganti "ini"/"tersebut" menghasilkan embedding yang tidak diskriminatif dan buruk untuk pencarian semantik.

FORMAT RESPONSE (JSON array only, tanpa markdown):
[
    "Pertanyaan 1?",
    "Pertanyaan 2?",
    "Pertanyaan 3?",
    "Pertanyaan 4?",
    "Pertanyaan 5?"
]"""


def _parse_questions_response(response_text: str) -> List[str]:
    """Parse the LLM response into a list of question strings."""

    # Try direct JSON parse
    try:
        result = json.loads(response_text.strip())
        if isinstance(result, list):
            return [q.strip() for q in result if isinstance(q, str) and q.strip()]
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            if isinstance(result, list):
                return [q.strip() for q in result if isinstance(q, str) and q.strip()]
        except json.JSONDecodeError:
            pass

    # Try finding a JSON array anywhere
    arr_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
    if arr_match:
        try:
            result = json.loads(arr_match.group(0))
            if isinstance(result, list):
                return [q.strip() for q in result if isinstance(q, str) and q.strip()]
        except json.JSONDecodeError:
            pass

    # Fallback: line-based extraction (numbered list)
    lines = response_text.strip().split('\n')
    questions = []
    for line in lines:
        line = line.strip()
        # Remove numbering: "1. ", "1) ", "- ", "* "
        cleaned = re.sub(r'^[\d]+[\.\)]\s*', '', line)
        cleaned = re.sub(r'^[-*]\s*', '', cleaned).strip()
        if cleaned and cleaned.endswith('?') and len(cleaned) > 10:
            questions.append(cleaned)

    return questions
