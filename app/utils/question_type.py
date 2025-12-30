import re
from typing import Dict, Optional

QUESTION_TYPE_BEHAVIORAL = "behavioral"
QUESTION_TYPE_NARRATIVE = "narrative"

_BEHAVIORAL_PATTERNS = [
    r"\btell me about a time\b",
    r"\bdescribe a time\b",
    r"\bgive me an example\b",
    r"\bshare an example\b",
    r"\bcan you share a time\b",
    r"\bwalk me through a time\b",
    r"\bwhen was the last time\b",
    r"\ba time you\b",
    r"\ba situation where\b",
    r"\bwhat did you do when\b",
    r"\bhow did you (handle|resolve|deal|approach|respond)\b",
]

_BEHAVIORAL_KEYWORDS = {
    "time",
    "situation",
    "example",
    "challenge",
    "conflict",
    "failure",
    "mistake",
    "disagreement",
    "pressure",
    "deadline",
    "ambiguity",
    "customer",
    "stakeholder",
    "leadership",
    "impact",
    "project",
}

_PROMPT_LEADS = ("tell me about", "describe", "give me", "share", "walk me through")


def normalize_question_text(text: Optional[str]) -> str:
    """Normalize question text for stable overrides keys."""
    return " ".join((text or "").strip().lower().split())


def infer_question_type(question: Optional[str]) -> str:
    """Infer question type using lightweight heuristics."""
    q = normalize_question_text(question)
    if not q:
        return QUESTION_TYPE_NARRATIVE

    for pattern in _BEHAVIORAL_PATTERNS:
        if re.search(pattern, q):
            return QUESTION_TYPE_BEHAVIORAL

    if q.startswith(_PROMPT_LEADS) and any(word in q for word in _BEHAVIORAL_KEYWORDS):
        return QUESTION_TYPE_BEHAVIORAL

    return QUESTION_TYPE_NARRATIVE


def resolve_question_type(question: Optional[str], overrides: Optional[Dict[str, str]] = None) -> str:
    """Resolve question type with overrides taking precedence."""
    key = normalize_question_text(question)
    if overrides and key in overrides:
        value = (overrides.get(key) or "").strip().lower()
        if value in {QUESTION_TYPE_BEHAVIORAL, QUESTION_TYPE_NARRATIVE}:
            return value
    return infer_question_type(question)
