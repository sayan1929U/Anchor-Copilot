from groq import Groq, APITimeoutError, APIConnectionError, APIError, RateLimitError
from app.config import settings

FALLBACK_MESSAGE = (
    "I am having trouble reaching my reasoning engine right now. "
    "Please try again in a moment - your message was not lost."
)

# Build the list of available keys, skipping any that weren't set.
_API_KEYS = [
    k for k in [settings.groq_api_key_1, settings.groq_api_key_2, settings.groq_api_key_3]
    if k
]

if not _API_KEYS:
    raise RuntimeError("No GROQ_API_KEY_1/2/3 configured in .env")

# One client per key, created once at import time rather than per-call.
_clients = [Groq(api_key=key, timeout=15.0, max_retries=1) for key in _API_KEYS]

# Tracks which key index to try first. Starts at 0 and only advances when a
# key actually gets rate-limited - successful calls don't rotate, so we keep
# using the same key until it's genuinely exhausted.
_current_key_index = 0


def safe_groq_call(**kwargs):
    """
    Wraps a Groq chat.completions.create call with automatic failover across
    multiple API keys. If the active key hits its daily/rate limit, we advance
    to the next key and retry immediately - the caller never sees the failure
    unless every configured key is exhausted or the network itself is down.
    """
    global _current_key_index

    keys_tried = 0
    index = _current_key_index

    while keys_tried < len(_clients):
        client = _clients[index]
        try:
            response = client.chat.completions.create(**kwargs)
            _current_key_index = index  # stick with this key for next call
            return response

        except RateLimitError:
            keys_tried += 1
            index = (index + 1) % len(_clients)
            continue

        except (APITimeoutError, APIConnectionError, APIError):
            return None

    # Every key is rate-limited
    return None
