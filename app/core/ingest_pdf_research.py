"""
Extracts text from Deloitte 2026 Gen Z/Millennial Survey PDFs, tags each page's
content with the matching agent category based on chapter markers, chunks it,
embeds it, and stores it in document_chunks alongside the policy docs.

Run: python -m app.core.ingest_pdf_research
"""
import os
import re
from pypdf import PdfReader
from app.database import SessionLocal
from app.models.document_chunk import DocumentChunk
from app.core.embeddings import embed_text

PDF_DIR = "data/research_pdfs"

# Maps chapter title keywords (as they appear in the PDF page headers) to your agent categories
CHAPTER_CATEGORY_MAP = [
    (r"financial pressure|delayed decisions|maybe later", "stability"),
    (r"leadership, reconsidered", "pathways"),
    (r"continuous learning|adaptability", "skills"),
    (r"ai and the readiness gap|readiness gap", "ai_fluency"),
    (r"well-being as infrastructure|well being as infrastructure", "recognition"),
    (r"ideal workplace|purpose and connection", "belonging"),
    (r"future they.re preparing|knowledge transfer", "early_careers"),
]

# Pages to skip entirely - covers, table of contents, methodology, disclaimers
SKIP_PATTERNS = [
    r"^table of contents",
    r"^research methodology",
    r"deloitte refers to one or more",
    r"^a letter from",
]


def detect_category(page_text: str) -> str | None:
    lowered = page_text.lower()
    for pattern, category in CHAPTER_CATEGORY_MAP:
        if re.search(pattern, lowered):
            return category
    return None


def should_skip(page_text: str) -> bool:
    lowered = page_text.lower().strip()
    return any(re.search(p, lowered) for p in SKIP_PATTERNS)


def chunk_text(text: str, max_chars: int = 500) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 40]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < max_chars:
            current = f"{current} {para}".strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def ingest_pdfs():
    db = SessionLocal()
    total = 0

    for filename in os.listdir(PDF_DIR):
        if not filename.endswith(".pdf"):
            continue

        filepath = os.path.join(PDF_DIR, filename)
        reader = PdfReader(filepath)

        current_category = None  # carries over across pages within the same chapter

        for page in reader.pages:
            page_text = page.extract_text() or ""
            if not page_text.strip() or should_skip(page_text):
                continue

            detected = detect_category(page_text)
            if detected:
                current_category = detected

            if not current_category:
                continue  # skip pages before the first chapter is detected (cover, intro)

            for chunk in chunk_text(page_text):
                vector = embed_text(chunk)
                doc = DocumentChunk(
                    source=filename,
                    category=current_category,
                    content=chunk,
                    embedding=vector,
                )
                db.add(doc)
                total += 1

    db.commit()
    db.close()
    print(f"Ingested {total} chunks from PDF research documents")


if __name__ == "__main__":
    ingest_pdfs()
