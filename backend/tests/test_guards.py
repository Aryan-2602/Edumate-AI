"""Unit tests for deterministic retrieval / output guards."""

from __future__ import annotations

from langchain.schema import Document

from app.guards.rag_answer import assess_rag_answer, rag_fallback_message
from app.guards.retrieval_context import assess_retrieval_for_generation
from app.guards.structured_output import (
    parse_json_array_from_llm,
    validate_flashcard_items,
    validate_quiz_items,
)


def test_retrieval_rejects_empty_results():
    a = assess_retrieval_for_generation(
        [],
        min_non_empty_chunks=1,
        min_total_chars=10,
        max_best_distance=None,
    )
    assert a.is_failure
    assert a.reason == "too_few_chunks"


def test_retrieval_rejects_short_context():
    docs = [
        (Document(page_content="hi", metadata={}), 0.1),
    ]
    a = assess_retrieval_for_generation(
        docs,
        min_non_empty_chunks=1,
        min_total_chars=100,
        max_best_distance=None,
    )
    assert a.is_failure
    assert a.reason == "context_too_short"


def test_retrieval_rejects_high_distance():
    docs = [
        (Document(page_content="x" * 50, metadata={}), 9.99),
    ]
    a = assess_retrieval_for_generation(
        docs,
        min_non_empty_chunks=1,
        min_total_chars=10,
        max_best_distance=1.0,
    )
    assert a.is_failure
    assert a.reason == "low_relevance"


def test_retrieval_accepts_strong_context():
    docs = [
        (Document(page_content="alpha beta gamma delta", metadata={}), 0.2),
    ]
    a = assess_retrieval_for_generation(
        docs,
        min_non_empty_chunks=1,
        min_total_chars=10,
        max_best_distance=2.0,
    )
    assert a.ok


def test_rag_answer_rejects_no_overlap():
    ctx = "photosynthesis converts light energy in plants"
    ans = "RSA decryption uses modular exponentiation with ciphertext blocks."
    a = assess_rag_answer(
        ans,
        context_text=ctx,
        question="What is photosynthesis?",
        min_answer_chars=5,
        min_context_word_overlap=1,
    )
    assert not a.ok


def test_rag_answer_accepts_grounded():
    ctx = "photosynthesis converts light energy in chloroplasts"
    ans = "Photosynthesis converts light energy, mainly in chloroplasts."
    a = assess_rag_answer(
        ans,
        context_text=ctx,
        question="explain photosynthesis",
        min_answer_chars=5,
        min_context_word_overlap=1,
    )
    assert a.ok


def test_parse_json_array_bracket_extract():
    raw = 'noise [{"a": 1}] trail'
    items, err = parse_json_array_from_llm(raw)
    assert err is None
    assert items == [{"a": 1}]


def test_parse_json_array_malformed():
    items, err = parse_json_array_from_llm("not json")
    assert items is None
    assert err == "malformed_json"


def test_validate_quiz_rejects_bad_options():
    items = [{"question": "Q?", "options": ["a"], "correct_answer": "A"}]
    ok, r = validate_quiz_items(items, 1)
    assert not ok


def test_validate_flashcards_requires_nonempty_fields():
    items = [{"front": "", "back": "x"}]
    ok, r = validate_flashcard_items(items, 1)
    assert not ok


def test_rag_fallback_message_includes_reason():
    m = rag_fallback_message("low_relevance")
    assert "low_relevance" in m
