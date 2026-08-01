import re

def _extract_claims(text: str) -> list[str]:
    """Pulls out concrete, checkable factual claims: numbers/percentages and
    capitalized multi-word phrases (likely program/policy names) - excluding
    self-citations (report titles, filenames, years) since those are citation
    labels, not factual claims that need independent verification."""
    claims = []

    numbers = re.findall(r"\b\d+(?:\.\d+)?%?\b", text)
    for n in numbers:
        # Skip bare 4-digit years (2020-2029 range) - these show up constantly in
        # citations ("2026 survey", filenames) and aren't themselves factual claims.
        bare_digits = n.rstrip("%")
        if re.fullmatch(r"20\d\d", bare_digits) and "%" not in n:
            continue
        numbers_ok = n
        claims.append(numbers_ok)

    phrase_candidates = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)+\b", text)

    CITATION_KEYWORDS = {"survey", "report", "study", "research"}
    for phrase in phrase_candidates:
        words = set(phrase.lower().split())
        if words & CITATION_KEYWORDS:
            continue
        claims.append(phrase)

    return list(set(claims))


def check_grounding(response_text: str, context_text: str) -> bool:
    if not context_text or context_text.strip() == "":
        return True

    claims = _extract_claims(response_text)
    if not claims:
        return True

    context_lower = context_text.lower()
    unsupported = [c for c in claims if c.lower() not in context_lower]
    unsupported = [c for c in unsupported if len(c) > 3]

    return len(unsupported) == 0
