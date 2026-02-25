"""GROBID service for PDF metadata extraction."""
import requests
from lxml import etree
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from app.config import get_settings
import sys
from app.services.llm import generate_response
settings = get_settings()



async def extract_header(file_bytes: bytes) -> dict:
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
        
        with open("grobid_header_response.txt", "w", encoding="utf-8") as f:
            f.write("==grobid header \n")
            f.write(response.text + "\n")
            f.write("=====================================\n")
        return { 
            "length": len(response.text),
            "header": response.text}

#         build_context = """
# Dari informasi dibawah ini, extract semua metadatanya, terutama dublin core metadata
# """
#         llm_response = await generate_response(build_context + '\n\n' + response.text)

#         with open("llm_response.txt", "w", encoding="utf-8") as f:
#             f.write("==respinse \n")
#             f.write(llm_response + "\n")
#             f.write("=====================================\n")

#         print('==reponse llm grobid')
#         print(llm_response)
#         print('=====================================')
#         print(build_context + '\n\n' + response.text)
#         return

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

        with open("full_text_grobid.txt", "w", encoding="utf-8") as f:
            f.write(response.text + "\n")
            f.write("=====================================\n")



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
        
        parts = []
        
        # 1. Extract header content (title page / page 1)
        # Title - try multiple XPath locations (same as extract_header)
        title_xpaths = [
            "//tei:titleStmt/tei:title[@type='main']",
            "//tei:titleStmt/tei:title[not(@type)]",
            "//tei:titleStmt/tei:title",
            "//tei:sourceDesc//tei:title[@level='a']",
            "//tei:analytic/tei:title",
        ]
        title_text = None
        for xpath in title_xpaths:
            title_nodes = root.xpath(xpath, namespaces=ns)
            for node in title_nodes:
                # Use itertext() to get ALL text including nested elements
                text = "".join(node.itertext()).strip()
                if text and len(text) > 3:
                    title_text = text
                    break
            if title_text:
                break
        
        if title_text:
            parts.append(title_text)
            print(f"GROBID fulltext: Title included: {title_text[:80]}")
        else:
            print("GROBID fulltext: WARNING - No title found in fulltext XML")
        
        # Authors
        authors_xml = root.xpath("//tei:author/tei:persName", namespaces=ns)
        author_names = []
        for author in authors_xml:
            forename = "".join(author.xpath("tei:forename/text()", namespaces=ns)) or ""
            surname = "".join(author.xpath("tei:surname/text()", namespaces=ns)) or ""
            full_name = f"{forename} {surname}".strip()
            if full_name:
                author_names.append(full_name)
        if author_names:
            parts.append("Authors: " + ", ".join(author_names))
        
        # Publisher / Journal
        publisher_nodes = root.xpath("//tei:publicationStmt/tei:publisher/text()", namespaces=ns)
        journal_nodes = root.xpath("//tei:sourceDesc//tei:title[@level='j']/text()", namespaces=ns)
        if publisher_nodes and publisher_nodes[0].strip():
            parts.append("Publisher: " + publisher_nodes[0].strip())
        if journal_nodes and journal_nodes[0].strip():
            parts.append("Journal: " + journal_nodes[0].strip())
        
        # Abstract
        abstract_nodes = root.xpath("//tei:profileDesc/tei:abstract//text()", namespaces=ns)
        if abstract_nodes:
            abstract_text = " ".join(t.strip() for t in abstract_nodes if t.strip())
            if abstract_text:
                parts.append("Abstract: " + abstract_text)
        
        # Keywords
        keyword_nodes = root.xpath("//tei:keywords//tei:term/text()", namespaces=ns)
        if keyword_nodes:
            parts.append("Keywords: " + ", ".join(k.strip() for k in keyword_nodes if k.strip()))
        
        # 2. Extract body content (paragraphs + section headings)
        body_elements = root.xpath("//tei:body//tei:head | //tei:body//tei:p", namespaces=ns)
        for elem in body_elements:
            text = "".join(elem.itertext()).strip()
            if text:
                parts.append(text)

        fulltext = "\n\n".join(parts)
        with open("fullbgtt.txt", "w", encoding="utf-8") as f:
            f.write(fulltext + "\n")
            f.write("=====================================\n")

        print(f"GROBID fulltext: {len(fulltext)} chars (header + body)")
        return fulltext
    except Exception as e:
        print(f"GROBID fulltext extraction error: {e}")
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


def extract_structured_fulltext(file_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extract structured full text from PDF using GROBID.
    Returns a list of structured sections preserving document structure.
    
    Each section dict has:
        - type: "title" | "authors" | "abstract" | "keywords" | "section" | "reference"
        - title: section heading (if applicable)
        - content: text content (for single-content sections)
        - paragraphs: list of paragraph strings (for body sections)
    
    This preserves ALL text from the document for smart chunking.
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
        return []
    
    try:
        root = etree.fromstring(response.text.encode("utf-8"))
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        sections = []
        
        # === 1. TITLE ===
        title_xpaths = [
            "//tei:titleStmt/tei:title[@type='main']",
            "//tei:titleStmt/tei:title[not(@type)]",
            "//tei:titleStmt/tei:title",
            "//tei:sourceDesc//tei:title[@level='a']",
            "//tei:analytic/tei:title",
        ]
        title_text = None
        for xpath in title_xpaths:
            title_nodes = root.xpath(xpath, namespaces=ns)
            for node in title_nodes:
                text = "".join(node.itertext()).strip()
                if text and len(text) > 3:
                    title_text = text
                    break
            if title_text:
                break
        
        if title_text:
            sections.append({
                "type": "title",
                "title": "Title",
                "content": title_text,
                "paragraphs": [title_text]
            })
        
        # === 2. AUTHORS ===
        authors_xml = root.xpath("//tei:author/tei:persName", namespaces=ns)
        author_names = []
        for author in authors_xml:
            forename = "".join(author.xpath("tei:forename/text()", namespaces=ns)) or ""
            surname = "".join(author.xpath("tei:surname/text()", namespaces=ns)) or ""
            full_name = f"{forename} {surname}".strip()
            if full_name:
                author_names.append(full_name)
        if author_names:
            authors_text = "Authors: " + ", ".join(author_names)
            sections.append({
                "type": "authors",
                "title": "Authors",
                "content": authors_text,
                "paragraphs": [authors_text]
            })
        
        # === 3. PUBLISHER / JOURNAL ===
        publisher_nodes = root.xpath("//tei:publicationStmt/tei:publisher/text()", namespaces=ns)
        journal_nodes = root.xpath("//tei:sourceDesc//tei:title[@level='j']/text()", namespaces=ns)
        pub_parts = []
        if publisher_nodes and publisher_nodes[0].strip():
            pub_parts.append("Publisher: " + publisher_nodes[0].strip())
        if journal_nodes and journal_nodes[0].strip():
            pub_parts.append("Journal: " + journal_nodes[0].strip())
        if pub_parts:
            pub_text = ". ".join(pub_parts)
            sections.append({
                "type": "section",
                "title": "Publication Info",
                "content": pub_text,
                "paragraphs": [pub_text]
            })
        
        # === 4. ABSTRACT ===
        abstract_nodes = root.xpath("//tei:profileDesc/tei:abstract//text()", namespaces=ns)
        if abstract_nodes:
            abstract_text = " ".join(t.strip() for t in abstract_nodes if t.strip())
            if abstract_text:
                sections.append({
                    "type": "abstract",
                    "title": "Abstract",
                    "content": abstract_text,
                    "paragraphs": [abstract_text]
                })
        
        # === 5. KEYWORDS ===
        keyword_nodes = root.xpath("//tei:keywords//tei:term/text()", namespaces=ns)
        if keyword_nodes:
            keywords_text = "Keywords: " + ", ".join(k.strip() for k in keyword_nodes if k.strip())
            sections.append({
                "type": "keywords",
                "title": "Keywords",
                "content": keywords_text,
                "paragraphs": [keywords_text]
            })
        
        # === 6. BODY SECTIONS (structured by <div> with <head>) ===
        body = root.xpath("//tei:body", namespaces=ns)
        if body:
            body_elem = body[0]
            # Get top-level divs (sections)
            divs = body_elem.xpath("tei:div", namespaces=ns)
            
            if divs:
                for div in divs:
                    # Get section heading
                    head_nodes = div.xpath("tei:head", namespaces=ns)
                    section_title = None
                    if head_nodes:
                        section_title = "".join(head_nodes[0].itertext()).strip()
                    
                    # Get all paragraphs in this section
                    paragraphs = []
                    for p in div.xpath("tei:p", namespaces=ns):
                        text = "".join(p.itertext()).strip()
                        if text:
                            paragraphs.append(text)
                    
                    # Also check for nested divs (subsections)
                    for sub_div in div.xpath("tei:div", namespaces=ns):
                        sub_head_nodes = sub_div.xpath("tei:head", namespaces=ns)
                        sub_title = None
                        if sub_head_nodes:
                            sub_title = "".join(sub_head_nodes[0].itertext()).strip()
                        
                        sub_paragraphs = []
                        for p in sub_div.xpath("tei:p", namespaces=ns):
                            text = "".join(p.itertext()).strip()
                            if text:
                                sub_paragraphs.append(text)
                        
                        if sub_paragraphs:
                            # Add subsection heading as context prefix
                            if sub_title:
                                sub_paragraphs[0] = f"[{sub_title}] {sub_paragraphs[0]}"
                            paragraphs.extend(sub_paragraphs)
                    
                    if paragraphs:
                        sections.append({
                            "type": "section",
                            "title": section_title or "Untitled Section",
                            "content": "\n\n".join(paragraphs),
                            "paragraphs": paragraphs
                        })
                    elif section_title:
                        # Section with heading but no body paragraphs — 
                        # could have direct text or figures
                        direct_text = "".join(div.itertext()).strip()
                        # Remove the heading text from direct_text
                        if section_title and direct_text.startswith(section_title):
                            direct_text = direct_text[len(section_title):].strip()
                        if direct_text:
                            sections.append({
                                "type": "section",
                                "title": section_title,
                                "content": direct_text,
                                "paragraphs": [direct_text]
                            })
            else:
                # No divs — fallback: get all paragraphs and headings directly
                paragraphs = []
                current_heading = None
                for elem in body_elem.xpath("tei:head | tei:p", namespaces=ns):
                    tag = etree.QName(elem.tag).localname
                    text = "".join(elem.itertext()).strip()
                    if not text:
                        continue
                    if tag == "head":
                        current_heading = text
                    else:
                        if current_heading:
                            text = f"[{current_heading}] {text}"
                            current_heading = None
                        paragraphs.append(text)
                
                if paragraphs:
                    sections.append({
                        "type": "section",
                        "title": "Body",
                        "content": "\n\n".join(paragraphs),
                        "paragraphs": paragraphs
                    })
        
        # === 7. REFERENCES ===
        ref_titles = root.xpath("//tei:listBibl//tei:biblStruct", namespaces=ns)
        if ref_titles:
            ref_texts = []
            for i, bib in enumerate(ref_titles):
                # Get the full text of each reference
                ref_parts = []
                # Authors
                ref_authors = bib.xpath(".//tei:author/tei:persName", namespaces=ns)
                author_strs = []
                for a in ref_authors:
                    fn = "".join(a.xpath("tei:forename/text()", namespaces=ns)) or ""
                    sn = "".join(a.xpath("tei:surname/text()", namespaces=ns)) or ""
                    name = f"{fn} {sn}".strip()
                    if name:
                        author_strs.append(name)
                if author_strs:
                    ref_parts.append(", ".join(author_strs))
                # Title
                ref_title = bib.xpath(".//tei:title/text()", namespaces=ns)
                if ref_title:
                    ref_parts.append(ref_title[0].strip())
                # Date
                ref_date = bib.xpath(".//tei:date/@when", namespaces=ns)
                if ref_date:
                    ref_parts.append(f"({ref_date[0]})")
                
                if ref_parts:
                    ref_texts.append(f"[{i+1}] " + ". ".join(ref_parts))
            
            if ref_texts:
                ref_content = "\n".join(ref_texts)
                sections.append({
                    "type": "reference",
                    "title": "References",
                    "content": ref_content,
                    "paragraphs": ref_texts
                })
        
        total_chars = sum(len(s.get("content", "")) for s in sections)
        print(f"GROBID structured: {len(sections)} sections, {total_chars} total chars")
        for s in sections:
            print(f"  [{s['type']}] {s.get('title', 'N/A')}: {len(s.get('paragraphs', []))} paragraphs, {len(s.get('content', ''))} chars")
        
        return sections
        
    except Exception as e:
        print(f"GROBID structured fulltext extraction error: {e}")
        return []
