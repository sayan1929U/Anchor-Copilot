from groq import Groq
from sqlalchemy.orm import Session
from app.config import settings
from app.agents.base import AgentResponse
from app.agents.specialists import (
    stability_agent, pathways_agent, skills_agent, ai_fluency_agent,
    recognition_agent, belonging_agent, early_careers_agent,
)
from app.core.guardrails import detect_crisis, CRISIS_RESOURCE_MESSAGE
from app.core.hallucination_check import check_grounding
from app.core.retrieval import retrieve_chunks
from app.core.nudges import evaluate_nudge
from app.core.memory import get_recent_history
from app.models.agent_log import AgentAuditLog
from app.models.manager_nudge import ManagerNudge

client = Groq(api_key=settings.groq_api_key)

VALID_INTENTS = [
    "stability", "pathways", "skills", "ai_fluency",
    "recognition", "belonging", "early_careers",
]

AGENT_DISPATCH = {
    "stability": stability_agent,
    "pathways": pathways_agent,
    "skills": skills_agent,
    "ai_fluency": ai_fluency_agent,
    "recognition": recognition_agent,
    "belonging": belonging_agent,
    "early_careers": early_careers_agent,
}

SYSTEM_PROMPT = """You are an intent classifier for a workplace career-support assistant.
Classify the employee message into EXACTLY ONE of these categories:

- stability: pay, finances, cost of living, financial pressure
- pathways: career growth, promotion, leadership path
- skills: learning, upskilling, courses, certifications
- ai_fluency: AI tools at work, feeling behind on AI, AI readiness
- recognition: feeling unseen, wellbeing, burnout, recognition at work
- belonging: purpose, team culture, feeling like they belong
- early_careers: onboarding, being new, Gen Z/Gen Alpha workplace questions

Respond with ONLY the category label - lowercase, no punctuation, no explanation, nothing else.
"""


def classify_intent(message: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ],
        temperature=0,
        max_tokens=10,
    )
    raw = response.choices[0].message.content or ""
    label = raw.strip().lower().strip(".").strip()

    if label in VALID_INTENTS:
        return label
    for intent in VALID_INTENTS:
        if intent in label:
            return intent
    return "skills"


def _log(db: Session, session_id: int, agent_name: str, action: str, reason: str):
    entry = AgentAuditLog(session_id=session_id, agent_name=agent_name, action=action, reason=reason)
    db.add(entry)
    db.commit()


def route(message: str, db: Session, session_id: int, employee_id: int) -> AgentResponse:
    if detect_crisis(message):
        _log(db, session_id, "guardrail", "escalated", "Crisis language detected in message")
        return AgentResponse(
            agent_name="guardrail_escalation",
            content=CRISIS_RESOURCE_MESSAGE,
            intent="crisis_escalation",
        )

    intent = classify_intent(message)
    agent_fn = AGENT_DISPATCH[intent]

    # Pull recent history BEFORE this message was logged, so the agent sees
    # prior turns as context, not including the current message twice
    history = get_recent_history(db, session_id, limit=6)

    result = agent_fn(message, history)
    result.intent = intent

    chunks = retrieve_chunks(message, category=intent, top_k=3)
    context_text = "\n\n".join(c.content for c in chunks)
    is_grounded = check_grounding(result.content, context_text)

    if not is_grounded:
        _log(db, session_id, result.agent_name, "blocked", "Response flagged as potentially ungrounded")
        result.content = (
            "I want to give you accurate information rather than guess. "
            "I'd recommend checking with HR directly or your team's documented policies."
        )
    else:
        _log(db, session_id, result.agent_name, "responded",
             f"Grounded response generated using sources: {result.sources}")

    nudge_decision = evaluate_nudge(intent)
    if nudge_decision.should_nudge:
        nudge = ManagerNudge(
            session_id=session_id,
            employee_id=employee_id,
            nudge_type=nudge_decision.nudge_type,
            message=nudge_decision.manager_message,
        )
        db.add(nudge)
        db.commit()
        _log(db, session_id, "nudge_system", "escalated", f"Manager nudge created: {nudge_decision.nudge_type}")

    return result
