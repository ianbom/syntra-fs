from pypdf import PdfReader

def extract_pages(pdf_path: str):
    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        raise Exception(f"Failed to read PDF: {str(e)}")

    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text.strip())

    return pages
