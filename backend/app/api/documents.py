from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import tempfile
import uuid
from datetime import datetime
from app.database import get_db, User, Document, DocumentChunk
from app.services.ai_service import AIService
from app.services.storage_service import StorageService
from app.api.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize services
ai_service = AIService()
storage_service = StorageService()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process a document"""
    try:
        # Validate file type
        allowed_types = ['pdf', 'docx', 'doc', 'txt', 'md']
        file_extension = file.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Generate unique S3 key
            s3_key = f"users/{current_user.id}/documents/{uuid.uuid4()}/{file.filename}"
            
            # Upload to S3
            storage_service.upload_fileobj(
                file_obj=file.file,
                s3_key=s3_key,
                content_type=file.content_type
            )
            
            # Process document with AI service
            documents = ai_service.process_document(temp_file_path, file_extension)
            
            # Create embeddings
            collection_name = f"user_{current_user.id}_docs"
            vector_store = ai_service.create_embeddings(documents, collection_name)
            
            # Save document metadata to database
            db_document = Document(
                user_id=current_user.id,
                title=title,
                file_name=file.filename,
                file_path=s3_key,
                file_size=len(content),
                file_type=file_extension,
                chunk_count=len(documents),
                is_processed=True
            )
            db.add(db_document)
            db.commit()
            db.refresh(db_document)
            
            # Save document chunks
            for i, doc in enumerate(documents):
                chunk = DocumentChunk(
                    document_id=db_document.id,
                    chunk_index=i,
                    content=doc.page_content,
                    embedding_id=f"chunk_{db_document.id}_{i}"
                )
                db.add(chunk)
            
            db.commit()
            
            logger.info(f"Document uploaded successfully: {file.filename} by user {current_user.id}")
            
            return {
                "message": "Document uploaded and processed successfully",
                "document_id": db_document.id,
                "title": db_document.title,
                "chunk_count": db_document.chunk_count,
                "file_size": db_document.file_size
            }
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )


@router.get("/")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents for the current user"""
    try:
        documents = db.query(Document).filter(Document.user_id == current_user.id).all()
        
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
                "updated_at": doc.updated_at
            }
            for doc in documents
        ]
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving documents"
        )


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details and content"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Get document chunks
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()
        
        # Generate presigned URL for download
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
                    "chunk_index": chunk.chunk_index
                }
                for chunk in chunks
            ],
            "created_at": document.created_at,
            "updated_at": document.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving document"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document and its associated data"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete from S3
        try:
            storage_service.delete_file(document.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete file from S3: {e}")
        
        # Delete chunks from database
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).delete()
        
        # Delete document from database
        db.delete(document)
        db.commit()
        
        logger.info(f"Document {document_id} deleted successfully by user {current_user.id}")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting document"
        )


@router.post("/{document_id}/reprocess")
async def reprocess_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reprocess a document to regenerate embeddings"""
    try:
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Download file from S3 to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{document.file_type}") as temp_file:
            storage_service.download_file(document.file_path, temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Reprocess document
            documents = ai_service.process_document(temp_file_path, document.file_type)
            
            # Delete old chunks
            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            
            # Create new embeddings
            collection_name = f"user_{current_user.id}_docs"
            vector_store = ai_service.create_embeddings(documents, collection_name)
            
            # Save new chunks
            for i, doc in enumerate(documents):
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_index=i,
                    content=doc.page_content,
                    embedding_id=f"chunk_{document_id}_{i}"
                )
                db.add(chunk)
            
            # Update document
            document.chunk_count = len(documents)
            document.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Document {document_id} reprocessed successfully")
            
            return {
                "message": "Document reprocessed successfully",
                "chunk_count": document.chunk_count
            }
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error reprocessing document"
        )
