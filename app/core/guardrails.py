import re

# Deliberately conservative - patterns strongly associated with crisis/self-harm risk,
# not just "having a bad day". False positives here are far less costly than false negatives.
CRISIS_PATTERNS = [
    r"\bsuicid\w*\b",
    r"\bkill myself\b",
    r"\bend my life\b",
    r"\bwant to die\b",
    r"\bself[\s-]?harm\b",
    r"\bhurting myself\b",
    r"\bno reason to (live|go on)\b",
    r"\bcan'?t (go on|do this anymore)\b",
]

CRISIS_RESOURCE_MESSAGE = (
    "I'm really glad you reached out, and I want to make sure you get support "
    "beyond what I'm able to give here. If you're in immediate danger, please "
    "contact emergency services right away. You can also reach a crisis support "
    "line for confidential support - in India, AASRA is available at 91-22-27546669, "
    "or you can reach out to your company's Employee Assistance Program for immediate "
    "confidential support. You don't have to go through this alone."
)


def detect_crisis(message: str) -> bool:
    """Conservative keyword-based crisis detection. Returns True if the message
    should be escalated immediately, bypassing normal agent routing."""
    lowered = message.lower()
    return any(re.search(pattern, lowered) for pattern in CRISIS_PATTERNS)
