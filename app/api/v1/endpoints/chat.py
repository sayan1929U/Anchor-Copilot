from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.conversation import ConversationSession, Message
from app.models.employee import Employee
from app.agents.orchestrator import route
from app.core.auth_deps import get_current_employee
from app.core.rate_limit import limiter

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: int | None = None

@router.post("/")
@limiter.limit("20/minute")
def chat(
    request: Request,
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_employee: Employee = Depends(get_current_employee),
):
    if body.session_id:
        session = db.query(ConversationSession).filter(
            ConversationSession.id == body.session_id,
            ConversationSession.employee_id == current_employee.id,
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found for this employee")
    else:
        session = ConversationSession(employee_id=current_employee.id)
        db.add(session)
        db.commit()
        db.refresh(session)

    result = route(body.message, db, session.id, current_employee.id)

    user_msg = Message(session_id=session.id, role="user", content=body.message)
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
