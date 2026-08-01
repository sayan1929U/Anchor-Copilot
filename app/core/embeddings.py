from sentence_transformers import SentenceTransformer

# Loaded once at import time - reused across every embed call, not reloaded per-request
_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> list[float]:
    """Convert a string into a 384-dim embedding vector."""
    vector = _model.encode(text, normalize_embeddings=True)
    return vector.tolist()
