from app.database import SessionLocal
from app.models.document_chunk import DocumentChunk
from app.core.embeddings import embed_text

POLICY_SOURCES = {
    "stability.md", "pathways.md", "skills.md", "ai_fluency.md",
    "recognition.md", "belonging.md", "early_careers.md",
}


def retrieve_chunks(query: str, category: str | None = None, top_k: int = 3) -> list[DocumentChunk]:
    """
    Retrieves top_k chunks, guaranteeing a mix of company policy docs and
    research docs rather than letting the larger research corpus crowd out
    policy content purely due to volume imbalance.
    """
    db = SessionLocal()
    try:
        query_vector = embed_text(query)

        base_q = db.query(DocumentChunk)
        if category:
            base_q = base_q.filter(DocumentChunk.category == category)

        # Reserve at least 1 slot for a policy doc match, rest open to anything
        policy_q = base_q.filter(DocumentChunk.source.in_(POLICY_SOURCES))
        policy_top = (
            policy_q.order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(1)
            .all()
        )

        remaining_k = top_k - len(policy_top)
        exclude_ids = [c.id for c in policy_top]

        rest_q = base_q
        if exclude_ids:
            rest_q = rest_q.filter(~DocumentChunk.id.in_(exclude_ids))

        rest_top = (
            rest_q.order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(remaining_k)
            .all()
        )

        return policy_top + rest_top
    finally:
        db.close()
