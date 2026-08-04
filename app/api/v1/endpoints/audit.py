from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.agent_log import AgentAuditLog
from app.models.manager_nudge import ManagerNudge
from app.core.auth_deps import require_manager
from app.models.employee import Employee

router = APIRouter()

@router.get("/logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    limit: int = 50,
    _manager: Employee = Depends(require_manager),
):
    logs = db.query(AgentAuditLog).order_by(AgentAuditLog.id.desc()).limit(limit).all()
    return [
        {
            "id": log.id, "session_id": log.session_id, "agent_name": log.agent_name,
            "action": log.action, "reason": log.reason, "created_at": log.created_at,
        }
        for log in logs
    ]

@router.get("/nudges")
def get_nudges(
    db: Session = Depends(get_db),
    status: str | None = None,
    _manager: Employee = Depends(require_manager),
):
    q = db.query(ManagerNudge)
    if status:
        q = q.filter(ManagerNudge.status == status)
    nudges = q.order_by(ManagerNudge.id.desc()).all()
    return [
        {
            "id": n.id, "employee_id": n.employee_id, "nudge_type": n.nudge_type,
            "message": n.message, "status": n.status, "created_at": n.created_at,
        }
        for n in nudges
    ]
