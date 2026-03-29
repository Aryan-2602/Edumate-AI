import hashlib
import logging
import mimetypes
import os
import tempfile
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import settings
from app.database import Document, DocumentChunk, User, get_db
from app.deps import get_ai_service, get_storage_service
from app.jobs.document_ingestion import run_ingestion_for_document
from app.rate_limit import limiter
from app.services.storage_service import LocalStorageService, S3StorageService, StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
@limiter.limit(settings.rate_limit_upload)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Upload file to storage; chunking and embedding run in a background task."""
    try:
        allowed_types = ["pdf", "docx", "doc", "txt", "md"]
        file_extension = file.filename.split(".")[-1].lower()

        if file_extension not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_types)}",
            )

        content = await file.read()
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {settings.max_upload_bytes} bytes",
            )

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{file_extension}"
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            s3_key = f"users/{current_user.id}/documents/{uuid.uuid4()}/{file.filename}"

            storage_service.upload_file(
                temp_file_path,
                s3_key,
                content_type=file.content_type,
            )

            collection_name = f"user_{current_user.id}_docs"
            content_hash = hashlib.sha256(content).hexdigest()

            db_document = Document(
                user_id=current_user.id,
                title=title,
                file_name=file.filename,
                file_path=s3_key,
                file_size=len(content),
                file_type=file_extension,
                chunk_count=0,
                is_processed=False,
                chroma_collection_name=collection_name,
                content_hash=content_hash,
                processing_status="pending",
                processing_error=None,
            )
            db.add(db_document)
            db.commit()
            db.refresh(db_document)

            background_tasks.add_task(
                run_ingestion_for_document,
                db_document.id,
                False,
            )

            logger.info(
                "Document upload accepted (processing async): id=%s file=%s user=%s",
                db_document.id,
                file.filename,
                current_user.id,
            )

            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "Upload accepted; processing continues in the background",
                    "document_id": db_document.id,
                    "title": db_document.title,
                    "processing_status": db_document.processing_status,
                    "chunk_count": db_document.chunk_count,
                    "file_size": db_document.file_size,
                },
            )

        finally:
            os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error uploading document: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}",
        )


@router.get("/")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents for the current user"""
    try:
        documents = db.query(Document).filter(
            Document.user_id == current_user.id
        ).all()

        return [
            {
                "id": doc.id,
                "title": doc.title,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "file_type": doc.file_type,
                "chunk_count": doc.chunk_count,
                "is_processed": doc.is_processed,
                "processing_status": doc.processing_status,
                "processing_error": doc.processing_error,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
                "chroma_collection_name": doc.chroma_collection_name,
                "content_hash": doc.content_hash,
                "embedding_updated_at": doc.embedding_updated_at,
            }
            for doc in documents
        ]

    except Exception as e:
        logger.error("Error listing documents: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving documents",
        )


@router.get("/{document_id}/download")
async def download_document_file(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Stream original file from disk when STORAGE_BACKEND=local (same-origin friendly)."""
    if settings.storage_backend != "local" or not isinstance(
        storage_service, LocalStorageService
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Direct download is only available when STORAGE_BACKEND=local",
        )

    try:
        document = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == current_user.id,
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        path = storage_service.absolute_path(document.file_path)
        if not path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on disk",
            )

        media_type, _ = mimetypes.guess_type(document.file_name)
        return FileResponse(
            path,
            filename=document.file_name,
            media_type=media_type or "application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error downloading document %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error downloading file",
        )


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Get document details and content"""
    try:
        document = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == current_user.id,
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

        if settings.storage_backend == "local":
            download_url = f"/api/v1/documents/{document_id}/download"
        else:
            if not isinstance(storage_service, S3StorageService):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Storage configuration error",
                )
            download_url = storage_service.get_file_url(document.file_path)

        return {
            "id": document.id,
            "title": document.title,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "file_type": document.file_type,
            "chunk_count": document.chunk_count,
            "is_processed": document.is_processed,
            "processing_status": document.processing_status,
            "processing_error": document.processing_error,
            "download_url": download_url,
            "chunks": [
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in chunks
            ],
            "created_at": document.created_at,
            "updated_at": document.updated_at,
            "chroma_collection_name": document.chroma_collection_name,
            "content_hash": document.content_hash,
            "embedding_updated_at": document.embedding_updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving document %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving document",
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Delete a document and its associated data"""
    try:
        document = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == current_user.id,
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        collection_name = f"user_{current_user.id}_docs"
        try:
            storage_service.delete_file(document.file_path)
        except Exception as e:
            logger.warning("Failed to delete file from S3: %s", e)

        get_ai_service().delete_document_vectors(collection_name, document_id)

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete()

        db.delete(document)
        db.commit()

        logger.info(
            "Document %s deleted successfully by user %s",
            document_id,
            current_user.id,
        )

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting document %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document",
        )


@router.post("/{document_id}/reprocess")
@limiter.limit(settings.rate_limit_upload)
async def reprocess_document(
    request: Request,
    background_tasks: BackgroundTasks,
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Queue reprocessing (re-chunk and re-embed) in the background."""
    try:
        document = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.user_id == current_user.id,
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        document.processing_status = "pending"
        document.processing_error = None
        document.is_processed = False
        db.commit()
        db.refresh(document)

        background_tasks.add_task(
            run_ingestion_for_document,
            document_id,
            True,
        )

        logger.info(
            "Document %s reprocess queued by user %s",
            document_id,
            current_user.id,
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Reprocessing queued; embeddings will refresh in the background",
                "document_id": document_id,
                "processing_status": document.processing_status,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error queuing reprocess for document %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reprocessing document",
        )
