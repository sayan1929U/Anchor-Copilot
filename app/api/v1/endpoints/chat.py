from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.conversation import ConversationSession, Message
from app.agents.orchestrator import route

router = APIRouter()

class ChatRequest(BaseModel):
    employee_id: int
    message: str
    session_id: int | None = None

@router.post("/")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if request.session_id:
        session = db.query(ConversationSession).filter(
            ConversationSession.id == request.session_id,
            ConversationSession.employee_id == request.employee_id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found for this employee")
    else:
        session = ConversationSession(employee_id=request.employee_id)
        db.add(session)
        db.commit()
        db.refresh(session)

    # route() pulls history internally BEFORE we log this message, avoiding duplication
    result = route(request.message, db, session.id, request.employee_id)

    user_msg = Message(session_id=session.id, role="user", content=request.message)
    db.add(user_msg)

    agent_msg = Message(
        session_id=session.id,
        role="agent",
        agent_name=result.agent_name,
        content=result.content,
    )
    db.add(agent_msg)
    db.commit()

    return {
        "intent": result.intent,
        "agent": result.agent_name,
        "reply": result.content,
        "sources": result.sources,
        "session_id": session.id,
    }
