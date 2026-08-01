"""
Ingests markdown policy docs from data/policy_docs/ into the document_chunks table.
Run manually whenever source docs change: python -m app.core.ingest
"""
import os
from app.database import SessionLocal
from app.models.document_chunk import DocumentChunk
from app.core.embeddings import embed_text

DOCS_DIR = "data/policy_docs"


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    """Naive paragraph-based chunking - splits on blank lines, merges short ones up to max_chars."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) < max_chars:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def ingest():
    db = SessionLocal()

    # Clear existing chunks so re-running this script doesn't duplicate data
    db.query(DocumentChunk).delete()
    db.commit()

    total = 0
    for filename in os.listdir(DOCS_DIR):
        if not filename.endswith(".md"):
            continue

        category = filename.replace(".md", "")
        filepath = os.path.join(DOCS_DIR, filename)

        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = chunk_text(raw_text)

        for chunk in chunks:
            vector = embed_text(chunk)
            doc = DocumentChunk(
                source=filename,
                category=category,
                content=chunk,
                embedding=vector,
            )
            db.add(doc)
            total += 1

    db.commit()
    db.close()
    print(f"Ingested {total} chunks from {DOCS_DIR}")


if __name__ == "__main__":
    ingest()
