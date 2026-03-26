from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from app.workflows.rag_qa_workflow import run
from app.workflows.errors import ValidationError
from app.workflows.types import RagAskInput, WorkflowContext


@dataclass
class FakeUser:
    id: str


class FakeAIService:
    def answer_question(
        self,
        question: str,
        collection_name: str,
        top_k: int = 5,
        document_ids: Optional[List[int]] = None,
        metrics_out: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "question": question,
            "answer": f"answer:{question}",
            "sources": [{"content": "c", "metadata": {"k": 1}}],
        }




class FakeGuardFallbackAIService:
    def answer_question(
        self,
        question: str,
        collection_name: str,
        top_k: int = 5,
        document_ids: Optional[List[int]] = None,
        metrics_out: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "question": question,
            "answer": "fallback answer text",
            "sources": [],
            "guard_fallback": True,
            "guard_reason": "retrieval:too_few_chunks",
        }


def test_rag_workflow_guard_fallback_lowers_confidence(db_session, settings):
    ctx = WorkflowContext(
        db=db_session,
        current_user=FakeUser(id="u1"),  # type: ignore[arg-type]
        ai_service=FakeGuardFallbackAIService(),  # type: ignore[arg-type]
        settings=settings,
        request_id=None,
    )
    result = run(ctx, RagAskInput(question="What is X?"))
    assert result.confidence_score == 0.25


def test_rag_workflow_empty_question_raises(db_session, settings):
    ctx = WorkflowContext(
        db=db_session,
        current_user=FakeUser(id="u1"),  # type: ignore[arg-type]
        ai_service=FakeAIService(),  # type: ignore[arg-type]
        settings=settings,
        request_id=None,
    )
    with pytest.raises(ValidationError):
        run(ctx, RagAskInput(question="   "))

