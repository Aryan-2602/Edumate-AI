from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import Settings
from app.database import User
from app.services.ai_service import AIService


@dataclass(frozen=True)
class WorkflowContext:
    db: Session
    current_user: User
    ai_service: AIService
    settings: Settings
    request_id: Optional[str] = None
    # time.perf_counter() at HTTP middleware start (for request_handling_ms / total_ms)
    request_start_perf: Optional[float] = None


@dataclass(frozen=True)
class RagAskInput:
    question: str
    document_ids: Optional[List[int]] = None
    top_k: Optional[int] = None


@dataclass(frozen=True)
class RagAskResult:
    question_id: int
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float


@dataclass(frozen=True)
class QuizGenInput:
    document_id: int
    num_questions: Optional[int] = None


@dataclass(frozen=True)
class QuizGenResult:
    quiz_id: int
    title: str
    description: str
    question_count: int
    questions: List[Dict[str, Any]]


@dataclass(frozen=True)
class FlashcardGenInput:
    document_id: int
    num_cards: Optional[int] = None


@dataclass(frozen=True)
class FlashcardGenResult:
    flashcard_set_id: int
    document_id: int
    flashcards: List[Dict[str, str]]
    total_cards: int

