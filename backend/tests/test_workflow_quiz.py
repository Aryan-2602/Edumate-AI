from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from app.database import Document, DocumentChunk
from app.workflows.errors import GuardrailError
from app.workflows.quiz_generation_workflow import run
from app.workflows.types import QuizGenInput, WorkflowContext


@dataclass
class FakeUser:
    id: str


class FakeAIService:
    def generate_quiz(
        self,
        content: str,
        num_questions: int = 5,
        metrics_out: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "question": "q1?",
                "options": ["a", "b", "c", "d"],
                "correct_answer": "A",
                "explanation": "because",
            }
        ]


def test_quiz_workflow_requires_document_content(db_session, settings):
    user = FakeUser(id="u1")
    doc = Document(
        user_id=user.id,
        title="t",
        file_name="f.pdf",
        file_path="s3://x",
        file_size=1,
        file_type="pdf",
        chunk_count=0,
        is_processed=True,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    ctx = WorkflowContext(
        db=db_session,
        current_user=user,  # type: ignore[arg-type]
        ai_service=FakeAIService(),  # type: ignore[arg-type]
        settings=settings,
    )
    with pytest.raises(GuardrailError):
        run(ctx, QuizGenInput(document_id=doc.id, num_questions=1))


def test_quiz_workflow_creates_quiz(db_session, settings):
    user = FakeUser(id="u1")
    doc = Document(
        user_id=user.id,
        title="t",
        file_name="f.pdf",
        file_path="s3://x",
        file_size=1,
        file_type="pdf",
        chunk_count=1,
        is_processed=True,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    db_session.add(
        DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="some content",
            embedding_id="e0",
        )
    )
    db_session.commit()

    ctx = WorkflowContext(
        db=db_session,
        current_user=user,  # type: ignore[arg-type]
        ai_service=FakeAIService(),  # type: ignore[arg-type]
        settings=settings,
    )
    result = run(ctx, QuizGenInput(document_id=doc.id, num_questions=1))
    assert result.quiz_id > 0
    assert result.question_count == 1

