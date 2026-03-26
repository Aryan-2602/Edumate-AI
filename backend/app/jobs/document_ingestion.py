"""Background document ingestion: download → chunk → embed → persist (own DB session)."""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import Document, DocumentChunk, SessionLocal
from app.deps import get_ai_service, get_storage_service
from app.services.ai_service import stamp_chunk_metadata

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


def _truncate_error(msg: str, max_len: int = 4000) -> str:
    msg = (msg or "").strip()
    return msg if len(msg) <= max_len else msg[: max_len - 3] + "..."


def run_ingestion_for_document(
    document_id: int,
    delete_vectors_first: bool = False,
) -> None:
    """
    Process one document after S3 upload. Uses a fresh DB session and singleton
    AI/storage services. Safe to call from FastAPI BackgroundTasks.
    """
    db: Session = SessionLocal()
    temp_path: str | None = None
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning(
                "document_ingestion_skipped document_id=%s reason=document_not_found",
                document_id,
            )
            return

        collection_name = doc.chroma_collection_name or f"user_{doc.user_id}_docs"
        doc.chroma_collection_name = collection_name

        doc.processing_status = STATUS_PROCESSING
        doc.processing_error = None
        db.commit()
        db.refresh(doc)

        ai_service = get_ai_service()
        storage_service = get_storage_service()

        fd, temp_path = tempfile.mkstemp(suffix=f".{doc.file_type or 'bin'}")
        os.close(fd)

        storage_service.download_file(doc.file_path, temp_path)

        with open(temp_path, "rb") as f:
            file_bytes = f.read()
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        if delete_vectors_first:
            try:
                ai_service.delete_document_vectors(collection_name, document_id)
            except Exception as e:
                logger.warning(
                    "document_ingestion vector_delete document_id=%s: %s",
                    document_id,
                    e,
                )

        documents = ai_service.process_document(temp_path, doc.file_type or "txt")

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete()
        db.commit()

        stamp_chunk_metadata(documents, doc.user_id, document_id)
        ai_service.create_embeddings(documents, collection_name)

        for i, page_doc in enumerate(documents):
            db.add(
                DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=page_doc.page_content,
                    embedding_id=f"chunk_{document_id}_{i}",
                )
            )

        doc.chunk_count = len(documents)
        doc.content_hash = content_hash
        doc.is_processed = True
        doc.processing_status = STATUS_COMPLETED
        doc.processing_error = None
        doc.embedding_updated_at = datetime.utcnow()
        doc.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            "document_ingestion_completed document_id=%s user_id=%s chunks=%s",
            document_id,
            doc.user_id,
            len(documents),
        )
    except Exception as e:
        logger.exception(
            "document_ingestion_failed document_id=%s delete_vectors_first=%s",
            document_id,
            delete_vectors_first,
        )
        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if doc:
                doc.processing_status = STATUS_FAILED
                doc.processing_error = _truncate_error(str(e))
                doc.is_processed = False
                doc.updated_at = datetime.utcnow()
                db.commit()
        except Exception as cleanup_err:
            logger.error(
                "document_ingestion_cleanup_failed document_id=%s: %s",
                document_id,
                cleanup_err,
            )
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.unlink(temp_path)
            except OSError as e:
                logger.warning("document_ingestion temp_delete %s: %s", temp_path, e)
        db.close()
