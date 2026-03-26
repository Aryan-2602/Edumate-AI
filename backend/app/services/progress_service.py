"""Upsert user progress rows (per user + optional document)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database import UserProgress

logger = logging.getLogger(__name__)


def _get_or_create(
    db: Session, user_id: str, document_id: Optional[int]
) -> UserProgress:
    row = (
        db.query(UserProgress)
        .filter(
            UserProgress.user_id == user_id,
            UserProgress.document_id == document_id,
        )
        .first()
    )
    if row is None:
        row = UserProgress(user_id=user_id, document_id=document_id)
        db.add(row)
        db.flush()
    return row


def record_question_asked(
    db: Session, user_id: str, document_id: Optional[int] = None
) -> None:
    try:
        row = _get_or_create(db, user_id, document_id)
        row.questions_asked = (row.questions_asked or 0) + 1
        row.last_studied = datetime.utcnow()
    except Exception as e:
        logger.warning("Progress update (question) skipped: %s", e)


def record_quiz_generated(
    db: Session, user_id: str, document_id: int
) -> None:
    try:
        row = _get_or_create(db, user_id, document_id)
        row.quizzes_taken = (row.quizzes_taken or 0) + 1
        row.last_studied = datetime.utcnow()
    except Exception as e:
        logger.warning("Progress update (quiz) skipped: %s", e)


def record_flashcards_generated(
    db: Session, user_id: str, document_id: int, card_count: int
) -> None:
    try:
        row = _get_or_create(db, user_id, document_id)
        row.flashcards_reviewed = (row.flashcards_reviewed or 0) + card_count
        row.last_studied = datetime.utcnow()
    except Exception as e:
        logger.warning("Progress update (flashcards) skipped: %s", e)
