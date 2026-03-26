"""Post-generation checks on RAG answers (deterministic)."""

from __future__ import annotations

import logging
import string
from dataclasses import dataclass

logger = logging.getLogger("edumate.guards")

_REFUSAL_PATTERNS = (
    "i cannot answer",
    "i can't answer",
    "i do not have",
    "i don't have",
    "no information",
    "not found in",
    "unable to answer",
)


@dataclass(frozen=True)
class RagAnswerAssessment:
    ok: bool
    reason: str = ""


def _normalize_words(text: str) -> set[str]:
    t = text.lower().translate(str.maketrans("", "", string.punctuation))
    return {w for w in t.split() if len(w) > 2}


def assess_rag_answer(
    answer: str,
    *,
    context_text: str,
    question: str,
    min_answer_chars: int,
    min_context_word_overlap: int,
) -> RagAnswerAssessment:
    a = (answer or "").strip()
    if len(a) < min_answer_chars:
        logger.warning(
            "guard_fallback rag_answer reason=empty_or_too_short len=%s min=%s",
            len(a),
            min_answer_chars,
        )
        return RagAnswerAssessment(False, "empty_or_too_short")

    low = a.lower()
    for p in _REFUSAL_PATTERNS:
        if p in low and len(a) < 320:
            logger.warning("guard_fallback rag_answer reason=model_refusal_pattern")
            return RagAnswerAssessment(False, "model_refusal_pattern")

    ctx_words = _normalize_words(context_text)
    ans_words = _normalize_words(a)
    q_words = _normalize_words(question)

    overlap = ans_words & ctx_words
    if ctx_words and len(overlap) < min_context_word_overlap:
        logger.warning(
            "guard_fallback rag_answer reason=no_context_overlap overlap=%s min=%s",
            len(overlap),
            min_context_word_overlap,
        )
        return RagAnswerAssessment(False, "no_context_overlap")

    if not ctx_words and q_words:
        if not (ans_words & q_words) and len(ans_words) > 3:
            logger.warning("guard_fallback rag_answer reason=no_question_overlap")
            return RagAnswerAssessment(False, "no_question_overlap")

    return RagAnswerAssessment(True, "")


def rag_fallback_message(reason: str) -> str:
    return (
        "I could not ground a reliable answer in your uploaded material "
        f"({reason}). Try narrowing to specific documents, adding more notes, "
        "or rephrasing your question."
    )
