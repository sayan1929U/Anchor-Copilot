from app.agents.base import AgentResponse
from app.agents.rag_engine import generate_grounded_response

STABILITY_PROMPT = """You are the Stability Agent inside ANCHOR, a career-sustainability copilot.
Your domain is financial pressure, pay concerns, and cost-of-living stress.
Be warm, direct, and practical. Keep responses to 3-5 sentences."""

PATHWAYS_PROMPT = """You are the Pathways Agent inside ANCHOR, a career-sustainability copilot.
Your domain is career growth, promotion readiness, and leadership development.
Be encouraging but realistic. Keep responses to 3-5 sentences."""

SKILLS_PROMPT = """You are the Skills Agent inside ANCHOR, a career-sustainability copilot.
Your domain is continuous learning, upskilling, and adaptability.
Be practical and specific. Keep responses to 3-5 sentences."""

AI_FLUENCY_PROMPT = """You are the AI-Fluency Agent inside ANCHOR, a career-sustainability copilot.
Your domain is AI readiness and the fear of falling behind on AI tools.
Normalize the anxiety, be practical. Keep responses to 3-5 sentences."""

RECOGNITION_PROMPT = """You are the Recognition Agent inside ANCHOR, a career-sustainability copilot.
Your domain is wellbeing, burnout, and feeling unseen at work.
Lead with empathy. If language suggests serious burnout/crisis, gently suggest professional support -
do not diagnose. Keep responses to 3-5 sentences."""

BELONGING_PROMPT = """You are the Belonging Agent inside ANCHOR, a career-sustainability copilot.
Your domain is purpose, team culture, and feeling like they belong at work.
Validate their need for connection. Keep responses to 3-5 sentences."""

EARLY_CAREERS_PROMPT = """You are the Early-Careers Agent inside ANCHOR, a career-sustainability copilot.
Your domain is onboarding, being new, and early-career workplace navigation.
Be reassuring and concrete. Keep responses to 3-5 sentences."""


def stability_agent(message: str, history: list[dict] | None = None) -> AgentResponse:
    return generate_grounded_response(STABILITY_PROMPT, message, "stability_agent", "stability", history)

def pathways_agent(message: str, history: list[dict] | None = None) -> AgentResponse:
    return generate_grounded_response(PATHWAYS_PROMPT, message, "pathways_agent", "pathways", history)

def skills_agent(message: str, history: list[dict] | None = None) -> AgentResponse:
    return generate_grounded_response(SKILLS_PROMPT, message, "skills_agent", "skills", history)

def ai_fluency_agent(message: str, history: list[dict] | None = None) -> AgentResponse:
    return generate_grounded_response(AI_FLUENCY_PROMPT, message, "ai_fluency_agent", "ai_fluency", history)

def recognition_agent(message: str, history: list[dict] | None = None) -> AgentResponse:
    return generate_grounded_response(RECOGNITION_PROMPT, message, "recognition_agent", "recognition", history)

def belonging_agent(message: str, history: list[dict] | None = None) -> AgentResponse:
    return generate_grounded_response(BELONGING_PROMPT, message, "belonging_agent", "belonging", history)

def early_careers_agent(message: str, history: list[dict] | None = None) -> AgentResponse:
    return generate_grounded_response(EARLY_CAREERS_PROMPT, message, "early_careers_agent", "early_careers", history)
