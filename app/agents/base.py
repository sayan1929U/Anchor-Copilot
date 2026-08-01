from dataclasses import dataclass, field

@dataclass
class AgentResponse:
    agent_name: str
    content: str
    intent: str | None = None
    sources: list[str] = field(default_factory=list)   # e.g. ["stability.md"]
