import logging
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import settings
from app.database import User, get_db
from app.deps import get_ai_service
from app.routing.intent_router import route_intent
from app.services.ai_service import AIService
from app.workflows import (
    flashcard_generation_workflow,
    quiz_generation_workflow,
    rag_qa_workflow,
)
from app.workflows.errors import GuardrailError, InternalError, NotFound, ValidationError
from app.workflows.types import (
    FlashcardGenInput,
    QuizGenInput,
    RagAskInput,
    WorkflowContext,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["artificial intelligence"])


class IntentRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=settings.question_max_length)
    intent: Optional[str] = Field(default=None)

    document_id: Optional[int] = Field(default=None, ge=1)
    document_ids: Optional[List[int]] = None
    top_k: Optional[int] = Field(default=None, ge=1, le=settings.rag_top_k_max)

    num_questions: Optional[int] = Field(
        default=None, ge=1, le=settings.quiz_questions_max
    )
    num_cards: Optional[int] = Field(default=None, ge=1, le=settings.flashcards_max)


@router.post("/intent")
async def intent_dispatch(
    request: Request,
    body: IntentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_service: AIService = Depends(get_ai_service),
):
    ctx = WorkflowContext(
        db=db,
        current_user=current_user,
        ai_service=ai_service,
        settings=settings,
        request_id=getattr(request.state, "request_id", None),
        request_start_perf=getattr(request.state, "request_start_perf", None),
    )

    decision = route_intent(prompt=body.prompt, intent=body.intent)

    try:
        if decision.intent == "quiz":
            if body.document_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="document_id is required for quiz intent",
                )
            result = quiz_generation_workflow.run(
                ctx,
                QuizGenInput(
                    document_id=body.document_id,
                    num_questions=body.num_questions,
                ),
            )
        elif decision.intent == "flashcards":
            if body.document_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="document_id is required for flashcards intent",
                )
            result = flashcard_generation_workflow.run(
                ctx,
                FlashcardGenInput(
                    document_id=body.document_id,
                    num_cards=body.num_cards,
                ),
            )
        else:
            result = rag_qa_workflow.run(
                ctx,
                RagAskInput(
                    question=body.prompt,
                    document_ids=body.document_ids,
                    top_k=body.top_k,
                ),
            )

        return {
            "selected_intent": decision.intent,
            "reason": decision.reason,
            "matched_keywords": decision.matched_keywords,
            "result": result.__dict__,
        }

    except NotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    except (ValidationError, GuardrailError) as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InternalError as e:
        raise HTTPException(status_code=500, detail=e.message)

