"""GROBID service for PDF metadata extraction."""
import requests
from lxml import etree
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from app.config import get_settings

settings = get_settings()


def extract_header(file_bytes: bytes) -> dict:
    """
    Extract header/metadata from PDF using GROBID processHeaderDocument endpoint.
    Returns Dublin Core compatible metadata.
    """
    url = f"{settings.GROBID_URL}/api/processHeaderDocument"
    
    try:
        response = requests.post(
            url,
            files={'input': ("document.pdf", file_bytes)},
            data={'consolidateHeader': '1'},
            headers={'Accept': 'application/xml'},
            timeout=60
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="GROBID service is not available. Please ensure GROBID is running."
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="GROBID request timed out. The PDF may be too large."
        )
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail=f"GROBID header extraction failed with status {response.status_code}"
        )
    
    try:
        root = etree.fromstring(response.text.encode("utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse GROBID XML response: {str(e)}"
        )
    
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    
    # Extract title - try multiple XPath locations
    title = None
    title_xpaths = [
        "//tei:titleStmt/tei:title[@type='main']/text()",  # Main title
        "//tei:titleStmt/tei:title[not(@type)]/text()",    # Title without type
        "//tei:titleStmt/tei:title/text()",                 # Any title in titleStmt
        "//tei:sourceDesc//tei:title[@level='a']/text()",   # Article title
        "//tei:analytic/tei:title/text()",                  # Analytic title
        "//tei:head/text()",                                 # Header text (first one)
    ]
    
    for xpath in title_xpaths:
        title_nodes = root.xpath(xpath, namespaces=ns)
        if title_nodes:
            # Get the first non-empty title
            for t in title_nodes:
                cleaned = t.strip() if t else ""
                if cleaned and len(cleaned) > 3:  # Minimum 4 chars
                    title = cleaned
                    print(f"GROBID: Found title via {xpath}: {title[:50]}...")
                    break
            if title:
                break
    
    # If still no title, try to extract from first paragraph or heading
    if not title:
        first_head = root.xpath("//tei:body//tei:head[1]/text()", namespaces=ns)
        if first_head and first_head[0].strip():
            title = first_head[0].strip()
            print(f"GROBID: Using first heading as title: {title[:50]}...")
    
    # Extract authors
    authors_xml = root.xpath("//tei:author/tei:persName", namespaces=ns)
    authors = []
    for author in authors_xml:
        forename = "".join(author.xpath("tei:forename/text()", namespaces=ns)) or ""
        surname = "".join(author.xpath("tei:surname/text()", namespaces=ns)) or ""
        full_name = f"{forename} {surname}".strip()
        if full_name:
            authors.append(full_name)
    
    # Extract other metadata
    doi_nodes = root.xpath("//tei:idno[@type='DOI']/text()", namespaces=ns)
    date_nodes = root.xpath("//tei:date[@type='published']/@when", namespaces=ns)
    if not date_nodes:
        date_nodes = root.xpath("//tei:date/text()", namespaces=ns)
    publisher_nodes = root.xpath("//tei:publicationStmt/tei:publisher/text()", namespaces=ns)
    journal_nodes = root.xpath("//tei:sourceDesc//tei:title[@level='j']/text()", namespaces=ns)
    abstract_nodes = root.xpath("//tei:profileDesc/tei:abstract//text()", namespaces=ns)
    keyword_nodes = root.xpath("//tei:keywords//tei:term/text()", namespaces=ns)
    
    print(f"GROBID: Extracted title = '{title}'")
    
    return {
        "title": title,
        "authors": authors,
        "doi": doi_nodes[0] if doi_nodes else None,
        "publication_date": date_nodes[0] if date_nodes else None,
        "publisher": publisher_nodes[0] if publisher_nodes else None,
        "journal": journal_nodes[0] if journal_nodes else None,
        "abstract": " ".join(abstract_nodes).strip() if abstract_nodes else None,
        "keywords": keyword_nodes if keyword_nodes else []
    }


def extract_fulltext(file_bytes: bytes) -> str:
    """
    Extract full text from PDF using GROBID processFulltextDocument endpoint.
    Returns plain text content.
    """
    url = f"{settings.GROBID_URL}/api/processFulltextDocument"
    
    try:
        response = requests.post(
            url,
            files={'input': ("document.pdf", file_bytes)},
            headers={'Accept': 'application/xml'},
            timeout=120
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="GROBID service is not available."
        )
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="GROBID fulltext extraction timed out."
        )
    
    if response.status_code != 200:
        return ""
    
    try:
        root = etree.fromstring(response.text.encode("utf-8"))
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        
        # Extract all paragraph text
        paragraphs = root.xpath("//tei:body//tei:p/text()", namespaces=ns)
        return "\n\n".join(paragraphs)
    except Exception:
        return ""


def extract_references(file_bytes: bytes) -> list[str]:
    """
    Extract reference titles from PDF using GROBID.
    Returns list of reference titles.
    """
    url = f"{settings.GROBID_URL}/api/processFulltextDocument"
    
    try:
        response = requests.post(
            url,
            files={'input': ("document.pdf", file_bytes)},
            headers={'Accept': 'application/xml'},
            timeout=60
        )
    except Exception:
        return []
    
    if response.status_code != 200:
        return []
    
    try:
        root = etree.fromstring(response.text.encode("utf-8"))
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        return root.xpath("//tei:listBibl//tei:title/text()", namespaces=ns)
    except Exception:
        return []


def format_for_database(metadata: dict, references: list[str] = None) -> dict:
    """
    Format extracted metadata to match Dublin Core database schema.
    """
    authors = metadata.get("authors", [])
    keywords = metadata.get("keywords", [])
    references = references or []
    
    # First author as creator, rest as contributors
    creator = authors[0] if authors else None
    contributor = ", ".join(authors[1:]) if len(authors) > 1 else None
    
    # Parse publication date
    raw_date = metadata.get("publication_date")
    parsed_date = None
    if raw_date:
        for fmt in ["%Y-%m-%d", "%Y-%m", "%Y", "%d %B %Y", "%B %Y"]:
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                continue
    # Get title - don't provide default here, let LLM fallback handle it if needed
    title = metadata.get("title")
    if title:
        title = title.strip()
        # Clean up common issues
        if title.lower() in ["untitled", "title", "untitled document", ""]:
            title = None
    
    return {
        "title": title or 'Untitled',
        "creator": creator,
        "keywords": ", ".join(keywords) if keywords else None,
        "description": metadata.get("abstract"),
        "publisher": metadata.get("publisher"),
        "contributor": contributor,
        "date": parsed_date,
        "format": "application/pdf",
        "identifier": metadata.get("doi"),
        "source": metadata.get("journal"),
        "language": "en",
        "relation": ", ".join(references[:10]) if references else None,
        "doi": metadata.get("doi"),
        "abstract": metadata.get("abstract"),
        "citation_count": len(references)
    }
