from groq import Groq, APITimeoutError, APIConnectionError, APIError
from app.config import settings

client = Groq(api_key=settings.groq_api_key, timeout=15.0, max_retries=2)

FALLBACK_MESSAGE = (
    "I am having trouble reaching my reasoning engine right now. "
    "Please try again in a moment - your message was not lost."
)


def safe_groq_call(**kwargs):
    """Wraps a Groq chat.completions.create call with graceful failure handling.
    Returns the raw response object on success, or None on failure."""
    try:
        return client.chat.completions.create(**kwargs)
    except (APITimeoutError, APIConnectionError, APIError):
        return None
