import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import Flashcard, FlashcardSet, Question, Quiz, QuizQuestion, User, get_db
from app.services.ai_service import AIService
from app.api.auth import get_current_user
from app.deps import get_ai_service
from app.config import settings
from app.rate_limit import limiter
from app.routing.intent_router import route_intent
from app.workflows.errors import GuardrailError, InternalError, NotFound, ValidationError
from app.workflows.types import (
    FlashcardGenInput,
    QuizGenInput,
    RagAskInput,
    WorkflowContext,
)
from app.workflows import (
    flashcard_generation_workflow,
    quiz_generation_workflow,
    rag_qa_workflow,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["artificial intelligence"])


def _parse_options(raw: Optional[str]) -> List:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=settings.question_max_length)
    document_ids: Optional[List[int]] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=settings.rag_top_k_max)


class QuizRequest(BaseModel):
    document_id: int = Field(..., ge=1)
    num_questions: Optional[int] = Field(
        default=None, ge=1, le=settings.quiz_questions_max
    )


class FlashcardRequest(BaseModel):
    document_id: int = Field(..., ge=1)
    num_cards: Optional[int] = Field(
        default=None, ge=1, le=settings.flashcards_max
    )


@router.post("/ask")
@limiter.limit(settings.rate_limit_ai_write)
async def ask_question(
    request: Request,
    body: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """Ask a question and get an AI-generated answer using RAG"""
    try:
        _ = route_intent(prompt=body.question, intent="rag")
        ctx = WorkflowContext(
            db=db,
            current_user=current_user,
            ai_service=ai_service,
            settings=settings,
            request_id=getattr(request.state, "request_id", None),
            request_start_perf=getattr(request.state, "request_start_perf", None),
        )
        result = rag_qa_workflow.run(
            ctx,
            RagAskInput(
                question=body.question,
                document_ids=body.document_ids,
                top_k=body.top_k,
            ),
        )

        logger.info("Question answered for user %s", current_user.id)
        return {
            "question_id": result.question_id,
            "question": result.question,
            "answer": result.answer,
            "sources": result.sources,
            "confidence_score": result.confidence_score,
        }
    except NotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    except (ValidationError, GuardrailError) as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InternalError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error("Error answering question: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating answer: {str(e)}",
        )


@router.post("/generate-quiz")
@limiter.limit(settings.rate_limit_ai_write)
async def generate_quiz(
    request: Request,
    body: QuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """Generate a quiz from a specific document"""
    try:
        _ = route_intent(prompt="quiz", intent="quiz")
        ctx = WorkflowContext(
            db=db,
            current_user=current_user,
            ai_service=ai_service,
            settings=settings,
            request_id=getattr(request.state, "request_id", None),
        )
        result = quiz_generation_workflow.run(
            ctx,
            QuizGenInput(
                document_id=body.document_id,
                num_questions=body.num_questions,
            ),
        )
        logger.info("Quiz generated for user %s", current_user.id)
        return {
            "quiz_id": result.quiz_id,
            "title": result.title,
            "description": result.description,
            "question_count": result.question_count,
            "questions": result.questions,
        }
    except NotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    except (ValidationError, GuardrailError) as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InternalError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error("Error generating quiz: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quiz: {str(e)}",
        )


@router.post("/generate-flashcards")
@limiter.limit(settings.rate_limit_ai_write)
async def generate_flashcards(
    request: Request,
    body: FlashcardRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    """Generate flashcards from a specific document"""
    try:
        _ = route_intent(prompt="flashcards", intent="flashcards")
        ctx = WorkflowContext(
            db=db,
            current_user=current_user,
            ai_service=ai_service,
            settings=settings,
            request_id=getattr(request.state, "request_id", None),
            request_start_perf=getattr(request.state, "request_start_perf", None),
        )
        result = flashcard_generation_workflow.run(
            ctx,
            FlashcardGenInput(
                document_id=body.document_id,
                num_cards=body.num_cards,
            ),
        )
        logger.info("Flashcards generated for user %s", current_user.id)
        return {
            "flashcard_set_id": result.flashcard_set_id,
            "document_id": result.document_id,
            "flashcards": result.flashcards,
            "total_cards": result.total_cards,
        }
    except NotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    except (ValidationError, GuardrailError) as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InternalError as e:
        raise HTTPException(status_code=500, detail=e.message)
    except Exception as e:
        logger.error("Error generating flashcards: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating flashcards: {str(e)}",
        )


@router.get("/questions")
async def get_user_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """Get user's question history"""
    try:
        questions = (
            db.query(Question)
            .filter(Question.user_id == current_user.id)
            .order_by(Question.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": q.id,
                "question": q.question_text,
                "answer": q.answer_text,
                "source_documents": q.source_documents,
                "confidence_score": q.confidence_score,
                "created_at": q.created_at,
            }
            for q in questions
        ]

    except Exception as e:
        logger.error("Error retrieving questions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving questions",
        )


@router.get("/quizzes")
async def get_user_quizzes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: Optional[int] = 50,
):
    """Get user's quiz history"""
    try:
        lim = max(1, min(limit or 20, 200))
        quizzes = (
            db.query(Quiz)
            .filter(Quiz.user_id == current_user.id)
            .order_by(Quiz.created_at.desc())
            .limit(lim)
            .all()
        )

        return [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "source_document_id": q.source_document_id,
                "question_count": q.question_count,
                "created_at": q.created_at,
            }
            for q in quizzes
        ]

    except Exception as e:
        logger.error("Error retrieving quizzes: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quizzes",
        )


@router.get("/flashcard-sets")
async def get_user_flashcard_sets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """List user's saved flashcard sets"""
    try:
        sets = (
            db.query(FlashcardSet)
            .filter(FlashcardSet.user_id == current_user.id)
            .order_by(FlashcardSet.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "source_document_id": s.source_document_id,
                "card_count": s.card_count,
                "created_at": s.created_at,
            }
            for s in sets
        ]
    except Exception as e:
        logger.error("Error listing flashcard sets: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving flashcard sets",
        )


@router.get("/flashcard-sets/{set_id}")
async def get_flashcard_set_detail(
    set_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a flashcard set with all cards"""
    try:
        fc_set = (
            db.query(FlashcardSet)
            .filter(
                FlashcardSet.id == set_id,
                FlashcardSet.user_id == current_user.id,
            )
            .first()
        )
        if not fc_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flashcard set not found",
            )
        cards = (
            db.query(Flashcard)
            .filter(Flashcard.flashcard_set_id == set_id)
            .order_by(Flashcard.id)
            .all()
        )
        return {
            "id": fc_set.id,
            "title": fc_set.title,
            "description": fc_set.description,
            "source_document_id": fc_set.source_document_id,
            "card_count": fc_set.card_count,
            "created_at": fc_set.created_at,
            "cards": [
                {"id": c.id, "front": c.front, "back": c.back} for c in cards
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving flashcard set %s: %s", set_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving flashcard set",
        )


@router.get("/quizzes/{quiz_id}")
async def get_quiz_details(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed quiz information including questions"""
    try:
        quiz = (
            db.query(Quiz)
            .filter(Quiz.id == quiz_id, Quiz.user_id == current_user.id)
            .first()
        )

        if not quiz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found",
            )

        questions = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz_id)
            .all()
        )

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
                    "options": _parse_options(q.options),
                    "correct_answer": q.correct_answer,
                    "explanation": q.explanation,
                }
                for q in questions
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving quiz %s: %s", quiz_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quiz",
        )


@router.get("/search")
@limiter.limit(settings.rate_limit_default)
async def search_documents(
    request: Request,
    query: str = Query(..., min_length=1, max_length=2000),
    current_user: User = Depends(get_current_user),
    top_k: Optional[int] = Query(None, ge=1, le=settings.rag_top_k_max),
    document_ids: Optional[str] = None,
    ai_service: AIService = Depends(get_ai_service),
):
    """Search through user's documents using semantic search"""
    try:
        collection_name = f"user_{current_user.id}_docs"
        k = top_k if top_k is not None else settings.rag_top_k_default
        k = max(1, min(k, settings.rag_top_k_max))
        doc_ids = None
        if document_ids:
            doc_ids = []
            for part in document_ids.split(","):
                part = part.strip()
                if part.isdigit():
                    doc_ids.append(int(part))

        similar_docs = ai_service.get_similar_documents(
            query=query,
            collection_name=collection_name,
            top_k=k,
            document_ids=doc_ids,
        )

        return {
            "query": query,
            "results": similar_docs,
            "total_results": len(similar_docs),
        }

    except Exception as e:
        logger.error("Error searching documents: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}",
        )
