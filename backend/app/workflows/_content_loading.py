from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database import Document, DocumentChunk
from app.workflows.errors import GuardrailError, NotFound


@dataclass(frozen=True)
class ContentLoadResult:
    text: str
    chunk_count: int


def load_document_text_for_generation(
    db: Session,
    *,
    user_id: str,
    document_id: int,
    max_chars: int,
) -> ContentLoadResult:
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user_id)
        .first()
    )
    if not document:
        raise NotFound("Document not found")

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    chunk_count = len(chunks)
    text = "\n\n".join(c.content for c in chunks)
    if len(text) > max_chars:
        text = text[:max_chars]
    if not text.strip():
        raise GuardrailError("Document has no indexed content to generate from")
    return ContentLoadResult(text=text, chunk_count=chunk_count)
