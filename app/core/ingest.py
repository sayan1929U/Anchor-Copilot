"""
Ingests markdown policy docs from data/policy_docs/ into the document_chunks table.
Run manually whenever source docs change: python -m app.core.ingest
"""
import os
from app.database import SessionLocal
from app.models.document_chunk import DocumentChunk
from app.core.embeddings import embed_text

DOCS_DIR = "data/policy_docs"


def read_text_file(filepath: str) -> str:
    """Reads a text file, trying UTF-8 first and falling back to cp1252 -
    Windows editors sometimes save smart quotes/em-dashes in cp1252 even
    when the file is otherwise plain text, which breaks strict UTF-8
    decoding on Linux (e.g. GitHub Actions runners)."""
    with open(filepath, "rb") as f:
        raw_bytes = f.read()
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("cp1252")


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
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
    db.query(DocumentChunk).delete()
    db.commit()

    total = 0
    for filename in os.listdir(DOCS_DIR):
        if not filename.endswith(".md"):
            continue

        category = filename.replace(".md", "")
        filepath = os.path.join(DOCS_DIR, filename)
        raw_text = read_text_file(filepath)

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
