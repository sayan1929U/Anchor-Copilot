from dataclasses import dataclass

@dataclass
class NudgeDecision:
    should_nudge: bool
    nudge_type: str | None = None
    manager_message: str | None = None


# Which intents are worth surfacing to a manager, and the templated nudge text.
# Not every intent warrants one - e.g. "skills" questions are usually self-directed,
# but "recognition" and prolonged "stability" concerns are worth a manager knowing about.
NUDGE_RULES = {
    "recognition": (
        "recognition",
        "An employee on your team recently shared that they're feeling unseen or burned out. "
        "Consider a quick check-in or acknowledgment of their recent work.",
    ),
    "early_careers": (
        "career_check_in",
        "A new team member recently expressed feeling lost during onboarding. "
        "A short informal check-in could help them feel more supported.",
    ),
    "pathways": (
        "career_check_in",
        "An employee expressed interest in growing toward a leadership role. "
        "Consider a career-development conversation at your next 1:1.",
    ),
}


def evaluate_nudge(intent: str) -> NudgeDecision:
    if intent not in NUDGE_RULES:
        return NudgeDecision(should_nudge=False)

    nudge_type, manager_message = NUDGE_RULES[intent]
    return NudgeDecision(should_nudge=True, nudge_type=nudge_type, manager_message=manager_message)
