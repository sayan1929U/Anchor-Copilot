from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from app.database import get_db
from app.models.agent_log import AgentAuditLog
from app.models.manager_nudge import ManagerNudge
from app.models.conversation import ConversationSession, Message
from app.core.auth_deps import require_manager
from app.models.employee import Employee

router = APIRouter()


@router.get("/message-volume")
def message_volume(
    days: int = Query(default=30, le=90),
    db: Session = Depends(get_db),
    _manager: Employee = Depends(require_manager),
):
    """Daily count of user messages - shows real usage trend, aggregated in SQL
    so no raw message text ever leaves the database for this endpoint."""
    results = (
        db.query(
            cast(Message.created_at, Date).label("day"),
            func.count(Message.id).label("count"),
        )
        .filter(Message.role == "user")
        .group_by("day")
        .order_by("day")
        .limit(days)
        .all()
    )
    return [{"date": str(r.day), "count": r.count} for r in results]


@router.get("/intent-distribution")
def intent_distribution(
    db: Session = Depends(get_db),
    _manager: Employee = Depends(require_manager),
):
    """Which specialist agents handle the most volume - reveals what employees
    actually need help with most, at an aggregate level only."""
    results = (
        db.query(
            AgentAuditLog.agent_name,
            func.count(AgentAuditLog.id).label("count"),
        )
        .filter(AgentAuditLog.action == "responded")
        .group_by(AgentAuditLog.agent_name)
        .order_by(func.count(AgentAuditLog.id).desc())
        .all()
    )
    return [{"agent": r.agent_name, "count": r.count} for r in results]


@router.get("/guardrail-actions")
def guardrail_actions(
    db: Session = Depends(get_db),
    _manager: Employee = Depends(require_manager),
):
    """Breakdown of every guardrail decision - responded (grounded), blocked
    (hallucination check caught something), escalated (crisis or nudge)."""
    results = (
        db.query(
            AgentAuditLog.action,
            func.count(AgentAuditLog.id).label("count"),
        )
        .group_by(AgentAuditLog.action)
        .all()
    )
    return [{"action": r.action, "count": r.count} for r in results]


@router.get("/grounding-rate-trend")
def grounding_rate_trend(
    days: int = Query(default=30, le=90),
    db: Session = Depends(get_db),
    _manager: Employee = Depends(require_manager),
):
    """Daily grounding rate - responded vs blocked, as a percentage per day.
    This is the metric that would catch a regression like the one we found
    and fixed during the eval suite work, but tracked continuously in production."""
    results = (
        db.query(
            cast(AgentAuditLog.created_at, Date).label("day"),
            AgentAuditLog.action,
            func.count(AgentAuditLog.id).label("count"),
        )
        .filter(AgentAuditLog.action.in_(["responded", "blocked"]))
        .group_by("day", AgentAuditLog.action)
        .order_by("day")
        .limit(days * 2)
        .all()
    )

    daily = {}
    for r in results:
        day_str = str(r.day)
        daily.setdefault(day_str, {"responded": 0, "blocked": 0})
        daily[day_str][r.action] = r.count

    output = []
    for day, counts in sorted(daily.items()):
        total = counts["responded"] + counts["blocked"]
        rate = round(counts["responded"] / total * 100, 1) if total else 100.0
        output.append({"date": day, "grounding_rate": rate, "total": total})

    return output


@router.get("/nudges-by-type")
def nudges_by_type(
    db: Session = Depends(get_db),
    _manager: Employee = Depends(require_manager),
):
    results = (
        db.query(
            ManagerNudge.nudge_type,
            func.count(ManagerNudge.id).label("count"),
        )
        .group_by(ManagerNudge.nudge_type)
        .all()
    )
    return [{"nudge_type": r.nudge_type, "count": r.count} for r in results]


@router.get("/active-employees")
def active_employees(
    days: int = Query(default=7, le=90),
    db: Session = Depends(get_db),
    _manager: Employee = Depends(require_manager),
):
    """Distinct employees who started at least one session in the window -
    a headcount, never a list of who they are, at this aggregation level."""
    count = (
        db.query(func.count(func.distinct(ConversationSession.employee_id)))
        .scalar()
    )
    return {"active_employees": count, "window_days": days}


@router.get("/multi-turn-rate")
def multi_turn_rate(
    db: Session = Depends(get_db),
    _manager: Employee = Depends(require_manager),
):
    """What share of sessions actually use multi-turn memory (3+ messages)
    vs one-shot questions - a real usage signal for the Phase 9 memory feature."""
    session_counts = (
        db.query(
            Message.session_id,
            func.count(Message.id).label("msg_count"),
        )
        .group_by(Message.session_id)
        .subquery()
    )

    total_sessions = db.query(func.count()).select_from(session_counts).scalar()
    multi_turn_sessions = (
        db.query(func.count())
        .select_from(session_counts)
        .filter(session_counts.c.msg_count >= 4)  # 4 rows = 2 user + 2 agent = a real back-and-forth
        .scalar()
    )

    rate = round(multi_turn_sessions / total_sessions * 100, 1) if total_sessions else 0.0
    return {
        "total_sessions": total_sessions,
        "multi_turn_sessions": multi_turn_sessions,
        "multi_turn_rate_pct": rate,
    }
