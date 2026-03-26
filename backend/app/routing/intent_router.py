from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Literal, Optional, Sequence, Tuple


Intent = Literal["rag", "quiz", "flashcards"]


@dataclass(frozen=True)
class RouteDecision:
    intent: Intent
    reason: str
    matched_keywords: List[str]


_QUIZ_KEYWORDS: Tuple[str, ...] = (
    "quiz",
    "mcq",
    "multiple choice",
    "test me",
    "practice questions",
)

_FLASHCARD_KEYWORDS: Tuple[str, ...] = (
    "flashcard",
    "flashcards",
    "anki",
    "memorize",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _match_keywords(normalized_prompt: str, keywords: Sequence[str]) -> List[str]:
    matched: List[str] = []
    for kw in keywords:
        if kw in normalized_prompt:
            matched.append(kw)
    return matched


def route_intent(
    *,
    prompt: str,
    intent: Optional[str],
) -> RouteDecision:
    """Select intent with explicit override + deterministic keyword fallback."""
    normalized = _normalize(prompt)
    explicit = _normalize(intent or "")
    if explicit in ("rag", "quiz", "flashcards"):
        return RouteDecision(
            intent=explicit,  # type: ignore[return-value]
            reason="explicit_intent",
            matched_keywords=[],
        )

    matched_quiz = _match_keywords(normalized, _QUIZ_KEYWORDS)
    if matched_quiz:
        return RouteDecision(intent="quiz", reason="keyword_match", matched_keywords=matched_quiz)

    matched_fc = _match_keywords(normalized, _FLASHCARD_KEYWORDS)
    if matched_fc:
        return RouteDecision(
            intent="flashcards",
            reason="keyword_match",
            matched_keywords=matched_fc,
        )

    return RouteDecision(intent="rag", reason="default", matched_keywords=[])

