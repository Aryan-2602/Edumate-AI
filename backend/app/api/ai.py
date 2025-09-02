from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db, User, Question, Quiz, QuizQuestion
from app.services.ai_service import AIService
from app.api.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["artificial intelligence"])

# Initialize AI service
ai_service = AIService()


class QuestionRequest(BaseModel):
    question: str
    document_ids: Optional[List[int]] = None
    top_k: Optional[int] = 5


class QuizRequest(BaseModel):
    document_id: int
    num_questions: Optional[int] = 5


class FlashcardRequest(BaseModel):
    document_id: int
    num_cards: Optional[int] = 10


@router.post("/ask")
async def ask_question(
    request: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Ask a question and get an AI-generated answer using RAG"""
    try:
        # Determine which collection to search
        if request.document_ids:
            # Search in specific documents
            collection_name = f"user_{current_user.id}_docs"
        else:
            # Search in all user documents
            collection_name = f"user_{current_user.id}_docs"
        
        # Get answer using AI service
        response = ai_service.answer_question(
            question=request.question,
            collection_name=collection_name,
            top_k=request.top_k
        )
        
        # Save question to database
        db_question = Question(
            user_id=current_user.id,
            question_text=request.question,
            answer_text=response["answer"],
            source_documents=str(request.document_ids) if request.document_ids else None,
            confidence_score=0.8  # Placeholder - could be calculated from similarity scores
        )
        db.add(db_question)
        db.commit()
        
        logger.info(f"Question answered successfully for user {current_user.id}")
        
        return {
            "question_id": db_question.id,
            "question": response["question"],
            "answer": response["answer"],
            "sources": response["sources"],
            "confidence_score": db_question.confidence_score
        }
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating answer: {str(e)}"
        )


@router.post("/generate-quiz")
async def generate_quiz(
    request: QuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a quiz from a specific document"""
    try:
        # Get document content (you might want to get this from the database)
        # For now, we'll use a placeholder approach
        # In a real implementation, you'd retrieve the document content
        
        # Generate quiz using AI service
        # Note: This is a simplified version - you'd need to get actual document content
        quiz_questions = ai_service.generate_quiz(
            content="Document content would go here",  # Placeholder
            num_questions=request.num_questions
        )
        
        # Save quiz to database
        db_quiz = Quiz(
            user_id=current_user.id,
            title=f"Quiz from Document {request.document_id}",
            description=f"AI-generated quiz with {request.num_questions} questions",
            source_document_id=request.document_id,
            question_count=len(quiz_questions)
        )
        db.add(db_quiz)
        db.commit()
        
        # Save quiz questions
        for question_data in quiz_questions:
            quiz_question = QuizQuestion(
                quiz_id=db_quiz.id,
                question_text=question_data["question"],
                correct_answer=question_data["correct_answer"],
                options=str(question_data["options"]),
                explanation=question_data.get("explanation", "")
            )
            db.add(quiz_question)
        
        db.commit()
        
        logger.info(f"Quiz generated successfully for user {current_user.id}")
        
        return {
            "quiz_id": db_quiz.id,
            "title": db_quiz.title,
            "description": db_quiz.description,
            "question_count": db_quiz.question_count,
            "questions": quiz_questions
        }
        
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quiz: {str(e)}"
        )


@router.post("/generate-flashcards")
async def generate_flashcards(
    request: FlashcardRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate flashcards from a specific document"""
    try:
        # Generate flashcards using AI service
        # Note: This is a simplified version - you'd need to get actual document content
        flashcards = ai_service.generate_flashcards(
            content="Document content would go here",  # Placeholder
            num_cards=request.num_cards
        )
        
        logger.info(f"Flashcards generated successfully for user {current_user.id}")
        
        return {
            "document_id": request.document_id,
            "flashcards": flashcards,
            "total_cards": len(flashcards)
        }
        
    except Exception as e:
        logger.error(f"Error generating flashcards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating flashcards: {str(e)}"
        )


@router.get("/questions")
async def get_user_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Optional[int] = 50
):
    """Get user's question history"""
    try:
        questions = db.query(Question).filter(
            Question.user_id == current_user.id
        ).order_by(Question.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": q.id,
                "question": q.question_text,
                "answer": q.answer_text,
                "source_documents": q.source_documents,
                "confidence_score": q.confidence_score,
                "created_at": q.created_at
            }
            for q in questions
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving questions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving questions"
        )


@router.get("/quizzes")
async def get_user_quizzes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Optional[int] = 20
):
    """Get user's quiz history"""
    try:
        quizzes = db.query(Quiz).filter(
            Quiz.user_id == current_user.id
        ).order_by(Quiz.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "source_document_id": q.source_document_id,
                "question_count": q.question_count,
                "created_at": q.created_at
            }
            for q in quizzes
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving quizzes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quizzes"
        )


@router.get("/quizzes/{quiz_id}")
async def get_quiz_details(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed quiz information including questions"""
    try:
        quiz = db.query(Quiz).filter(
            Quiz.id == quiz_id,
            Quiz.user_id == current_user.id
        ).first()
        
        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        # Get quiz questions
        questions = db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id == quiz_id
        ).all()
        
        return {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "source_document_id": quiz.source_document_id,
            "question_count": quiz.question_count,
            "created_at": quiz.created_at,
            "questions": [
                {
                    "id": q.id,
                    "question": q.question_text,
                    "options": eval(q.options) if q.options else [],
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation
                }
                for q in questions
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving quiz {quiz_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quiz"
        )


@router.get("/search")
async def search_documents(
    query: str,
    current_user: User = Depends(get_current_user),
    top_k: Optional[int] = 5
):
    """Search through user's documents using semantic search"""
    try:
        collection_name = f"user_{current_user.id}_docs"
        
        similar_docs = ai_service.get_similar_documents(
            query=query,
            collection_name=collection_name,
            top_k=top_k
        )
        
        return {
            "query": query,
            "results": similar_docs,
            "total_results": len(similar_docs)
        }
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}"
        )
