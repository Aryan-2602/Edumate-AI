"""Background document ingestion job and status fields."""

from __future__ import annotations

from langchain.schema import Document as LCDocument

from app.database import Document, SessionLocal, User
from app.jobs.document_ingestion import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    run_ingestion_for_document,
)


def _ensure_user(db, uid: str = "ingest_u1"):
    if db.query(User).filter(User.id == uid).first():
        return
    db.add(
        User(
            id=uid,
            email=f"{uid}@test.local",
            display_name="Tester",
        )
    )
    db.commit()


def test_run_ingestion_completes_and_writes_chunks(db_session, monkeypatch):
    _ensure_user(db_session)
    doc = Document(
        user_id="ingest_u1",
        title="t",
        file_name="f.txt",
        file_path="s3://fake/key",
        file_size=4,
        file_type="txt",
        chunk_count=0,
        is_processed=False,
        chroma_collection_name="user_ingest_u1_docs",
        content_hash=None,
        processing_status="pending",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    doc_id = doc.id

    def fake_download(s3_key: str, local_path: str) -> bool:
        with open(local_path, "wb") as fp:
            fp.write(b"hello world content for chunking")
        return True

    class FakeAI:
        def process_document(self, file_path: str, file_type: str):
            return [
                LCDocument(page_content="only chunk", metadata={"source": file_path})
            ]

        def create_embeddings(self, documents, collection_name):
            return None

        def delete_document_vectors(self, collection_name, document_id):
            return None

    monkeypatch.setattr(
        "app.jobs.document_ingestion.get_storage_service",
        lambda: type(
            "S",
            (),
            {"download_file": staticmethod(fake_download)},
        )(),
    )
    monkeypatch.setattr(
        "app.jobs.document_ingestion.get_ai_service",
        lambda: FakeAI(),
    )

    run_ingestion_for_document(doc_id, delete_vectors_first=False)

    db2 = SessionLocal()
    try:
        d = db2.query(Document).filter(Document.id == doc_id).one()
        assert d.processing_status == STATUS_COMPLETED
        assert d.is_processed is True
        assert d.chunk_count == 1
        assert d.content_hash
        assert d.processing_error is None
        chunks = d.chunks
        assert len(chunks) == 1
        assert chunks[0].content == "only chunk"
    finally:
        db2.close()


def test_run_ingestion_marks_failed_on_error(db_session, monkeypatch):
    _ensure_user(db_session)
    doc = Document(
        user_id="ingest_u1",
        title="t",
        file_name="f.txt",
        file_path="s3://fake/key",
        file_size=4,
        file_type="txt",
        chunk_count=0,
        is_processed=False,
        chroma_collection_name="user_ingest_u1_docs",
        processing_status="pending",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    doc_id = doc.id

    def fake_download(s3_key: str, local_path: str) -> bool:
        with open(local_path, "wb") as fp:
            fp.write(b"x")
        return True

    class BoomAI:
        def process_document(self, file_path: str, file_type: str):
            raise RuntimeError("simulated embedding failure")

        def create_embeddings(self, documents, collection_name):
            return None

        def delete_document_vectors(self, collection_name, document_id):
            return None

    monkeypatch.setattr(
        "app.jobs.document_ingestion.get_storage_service",
        lambda: type(
            "S",
            (),
            {"download_file": staticmethod(fake_download)},
        )(),
    )
    monkeypatch.setattr(
        "app.jobs.document_ingestion.get_ai_service",
        lambda: BoomAI(),
    )

    run_ingestion_for_document(doc_id, delete_vectors_first=False)

    db2 = SessionLocal()
    try:
        d = db2.query(Document).filter(Document.id == doc_id).one()
        assert d.processing_status == STATUS_FAILED
        assert d.is_processed is False
        assert d.processing_error
        assert "simulated embedding failure" in d.processing_error
    finally:
        db2.close()


def test_run_ingestion_noop_when_document_deleted(caplog):
    import logging

    caplog.set_level(logging.WARNING)
    run_ingestion_for_document(999999, False)
    assert any(
        "document_ingestion_skipped" in r.getMessage()
        for r in caplog.records
    )
