from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from app.database import Document, DocumentChunk, Flashcard, FlashcardSet
from app.workflows.flashcard_generation_workflow import run
from app.workflows.types import FlashcardGenInput, WorkflowContext


@dataclass
class FakeUser:
    id: str


class FakeAIService:
    def generate_flashcards(
        self,
        content: str,
        num_cards: int = 10,
        metrics_out: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        return [{"front": "f1", "back": "b1"}]


def test_flashcard_workflow_persists_set_and_cards(db_session, settings):
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
    result = run(ctx, FlashcardGenInput(document_id=doc.id, num_cards=1))
    assert result.flashcard_set_id > 0
    assert result.total_cards == 1

    saved_set = db_session.query(FlashcardSet).filter(FlashcardSet.id == result.flashcard_set_id).one()
    saved_cards = (
        db_session.query(Flashcard)
        .filter(Flashcard.flashcard_set_id == result.flashcard_set_id)
        .all()
    )
    assert saved_set.card_count == 1
    assert len(saved_cards) == 1

