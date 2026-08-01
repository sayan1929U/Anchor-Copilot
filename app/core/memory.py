from sqlalchemy.orm import Session
from app.models.conversation import Message


def get_recent_history(db: Session, session_id: int, limit: int = 6) -> list[dict]:
    """
    Returns the last `limit` messages for a session, oldest first, formatted
    for inclusion in an LLM prompt. Limited to a small window (not the full
    history) to keep prompts short and avoid unbounded token growth as a
    conversation gets long.
    """
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.id.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()  # oldest first, so the LLM reads them in chronological order

    history = []
    for m in messages:
        role = "user" if m.role == "user" else "assistant"
        history.append({"role": role, "content": m.content})
    return history
