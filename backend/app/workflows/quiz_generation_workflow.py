from __future__ import annotations

import json

from app.database import Quiz, QuizQuestion
from app.observability.workflow_metrics import (
    STAGE_CONTENT_LOAD,
    STAGE_GENERATION,
    STAGE_NORMALIZE,
    STAGE_POSTPROCESS,
    WorkflowMetricsCollector,
)
from app.services import progress_service
from app.workflows._content_loading import load_document_text_for_generation
from app.workflows.errors import GuardrailError, ValidationError
from app.workflows.types import QuizGenInput, QuizGenResult, WorkflowContext


def run(ctx: WorkflowContext, inp: QuizGenInput) -> QuizGenResult:
    collector = WorkflowMetricsCollector(
        request_id=ctx.request_id,
        user_id=ctx.current_user.id,
        document_id=inp.document_id,
        request_start_perf=ctx.request_start_perf,
    )
    collector.request_handling_cut()

    collector.start_stage(STAGE_NORMALIZE)
    if inp.document_id < 1:
        collector.flush_stage()
        raise ValidationError("document_id must be >= 1")
    num_questions = (
        inp.num_questions
        if inp.num_questions is not None
        else ctx.settings.quiz_questions_default
    )
    if num_questions < 1 or num_questions > ctx.settings.quiz_questions_max:
        collector.flush_stage()
        raise ValidationError("num_questions out of bounds")
    collector.flush_stage()

    collector.start_stage(STAGE_CONTENT_LOAD)
    loaded = load_document_text_for_generation(
        ctx.db,
        user_id=ctx.current_user.id,
        document_id=inp.document_id,
        max_chars=ctx.settings.content_join_max_chars,
    )
    collector.set_retrieved_chunks(loaded.chunk_count)
    collector.flush_stage()

    collector.start_stage(STAGE_GENERATION)
    metrics_aux: dict = {}
    try:
        quiz_questions = ctx.ai_service.generate_quiz(
            content=loaded.text, num_questions=num_questions, metrics_out=metrics_aux
        )
    except ValueError as e:
        raise GuardrailError(str(e)) from e
    collector.set_token_usage(metrics_aux.get("token_usage"))
    collector.flush_stage()

    collector.start_stage(STAGE_POSTPROCESS)
    db_quiz = Quiz(
        user_id=ctx.current_user.id,
        title=f"Quiz from Document {inp.document_id}",
        description=f"AI-generated quiz with {num_questions} questions",
        source_document_id=inp.document_id,
        question_count=len(quiz_questions),
    )
    ctx.db.add(db_quiz)
    ctx.db.commit()
    ctx.db.refresh(db_quiz)

    for q in quiz_questions:
        ctx.db.add(
            QuizQuestion(
                quiz_id=db_quiz.id,
                question_text=q["question"],
                correct_answer=q["correct_answer"],
                options=json.dumps(q["options"]),
                explanation=q.get("explanation", ""),
            )
        )
    ctx.db.commit()

    progress_service.record_quiz_generated(
        ctx.db, ctx.current_user.id, inp.document_id
    )
    ctx.db.commit()
    collector.flush_stage()
    collector.emit(workflow="quiz_generation", error=None)

    return QuizGenResult(
        quiz_id=db_quiz.id,
        title=db_quiz.title,
        description=db_quiz.description,
        question_count=db_quiz.question_count,
        questions=quiz_questions,
    )
