import hashlib
import logging
import os
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import settings
from app.database import Document, DocumentChunk, User, get_db
from app.deps import get_ai_service, get_storage_service
from app.rate_limit import limiter
from app.services.ai_service import AIService, stamp_chunk_metadata
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload")
@limiter.limit(settings.rate_limit_upload)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Upload and process a document"""
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

            documents = ai_service.process_document(temp_file_path, file_extension)
            collection_name = f"user_{current_user.id}_docs"
            content_hash = hashlib.sha256(content).hexdigest()

            db_document = Document(
                user_id=current_user.id,
                title=title,
                file_name=file.filename,
                file_path=s3_key,
                file_size=len(content),
                file_type=file_extension,
                chunk_count=len(documents),
                is_processed=True,
                chroma_collection_name=collection_name,
                content_hash=content_hash,
            )
            db.add(db_document)
            db.commit()
            db.refresh(db_document)

            stamp_chunk_metadata(documents, current_user.id, db_document.id)
            ai_service.create_embeddings(documents, collection_name)

            for i, doc in enumerate(documents):
                chunk = DocumentChunk(
                    document_id=db_document.id,
                    chunk_index=i,
                    content=doc.page_content,
                    embedding_id=f"chunk_{db_document.id}_{i}",
                )
                db.add(chunk)

            db_document.embedding_updated_at = datetime.utcnow()
            db.commit()

            logger.info(
                "Document uploaded successfully: %s by user %s",
                file.filename,
                current_user.id,
            )

            return {
                "message": "Document uploaded and processed successfully",
                "document_id": db_document.id,
                "title": db_document.title,
                "chunk_count": db_document.chunk_count,
                "file_size": db_document.file_size,
            }

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

        download_url = storage_service.get_file_url(document.file_path)

        return {
            "id": document.id,
            "title": document.title,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "file_type": document.file_type,
            "chunk_count": document.chunk_count,
            "is_processed": document.is_processed,
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
    ai_service: AIService = Depends(get_ai_service),
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

        ai_service.delete_document_vectors(collection_name, document_id)

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
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
    storage_service: StorageService = Depends(get_storage_service),
):
    """Reprocess a document to regenerate embeddings"""
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

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f".{document.file_type}"
        ) as temp_file:
            storage_service.download_file(document.file_path, temp_file.name)
            temp_file_path = temp_file.name

        try:
            collection_name = f"user_{current_user.id}_docs"
            ai_service.delete_document_vectors(collection_name, document_id)

            with open(temp_file_path, "rb") as f:
                file_bytes = f.read()
            content_hash = hashlib.sha256(file_bytes).hexdigest()

            documents = ai_service.process_document(
                temp_file_path, document.file_type
            )

            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()

            stamp_chunk_metadata(documents, current_user.id, document_id)
            ai_service.create_embeddings(documents, collection_name)

            for i, doc in enumerate(documents):
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=doc.page_content,
                    embedding_id=f"chunk_{document_id}_{i}",
                )
                db.add(chunk)

            document.chunk_count = len(documents)
            document.chroma_collection_name = collection_name
            document.content_hash = content_hash
            document.embedding_updated_at = datetime.utcnow()
            document.updated_at = datetime.utcnow()

            db.commit()

            logger.info("Document %s reprocessed successfully", document_id)

            return {
                "message": "Document reprocessed successfully",
                "chunk_count": document.chunk_count,
            }

        finally:
            os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error reprocessing document %s: %s", document_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reprocessing document",
        )
