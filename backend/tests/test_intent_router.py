from __future__ import annotations

from app.routing.intent_router import route_intent


def test_explicit_intent_overrides_keywords():
    d = route_intent(prompt="make me flashcards", intent="rag")
    assert d.intent == "rag"
    assert d.reason == "explicit_intent"


def test_quiz_keyword_routes_to_quiz():
    d = route_intent(prompt="Can you make a quiz for me?", intent=None)
    assert d.intent == "quiz"
    assert d.reason == "keyword_match"


def test_flashcard_keyword_routes_to_flashcards():
    d = route_intent(prompt="Generate FlashCards please", intent=None)
    assert d.intent == "flashcards"
    assert d.reason == "keyword_match"


def test_ambiguous_defaults_to_rag():
    d = route_intent(prompt="Explain photosynthesis", intent=None)
    assert d.intent == "rag"
    assert d.reason == "default"

