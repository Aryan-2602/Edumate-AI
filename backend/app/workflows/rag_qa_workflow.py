from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.database import Question
from app.observability.workflow_metrics import (
    STAGE_GENERATION,
    STAGE_POSTPROCESS,
    STAGE_RETRIEVAL,
    STAGE_NORMALIZE,
    WorkflowMetricsCollector,
)
from app.services import progress_service
from app.workflows.errors import GuardrailError, ValidationError
from app.workflows.types import RagAskInput, RagAskResult, WorkflowContext


def _normalize_question(question: str) -> str:
    return (question or "").strip()


def run(ctx: WorkflowContext, inp: RagAskInput) -> RagAskResult:
    _ids = inp.document_ids
    _single_doc: Optional[int] = (
        _ids[0] if _ids and len(_ids) == 1 else None
    )
    collector = WorkflowMetricsCollector(
        request_id=ctx.request_id,
        user_id=ctx.current_user.id,
        document_id=_single_doc,
        document_ids=_ids,
        request_start_perf=ctx.request_start_perf,
    )
    collector.request_handling_cut()

    collector.start_stage(STAGE_NORMALIZE)
    question = _normalize_question(inp.question)
    document_ids = inp.document_ids or None
    top_k = inp.top_k if inp.top_k is not None else ctx.settings.rag_top_k_default

    if not question:
        collector.flush_stage()
        raise ValidationError("Question must not be empty")
    if len(question) > ctx.settings.question_max_length:
        collector.flush_stage()
        raise GuardrailError("Question exceeds maximum length")
    if top_k < 1 or top_k > ctx.settings.rag_top_k_max:
        collector.flush_stage()
        raise ValidationError("top_k out of bounds")
    collector.flush_stage()

    collection_name = f"user_{ctx.current_user.id}_docs"
    metrics_aux: Dict[str, Any] = {}
    response = ctx.ai_service.answer_question(
        question=question,
        collection_name=collection_name,
        top_k=top_k,
        document_ids=document_ids,
        metrics_out=metrics_aux,
    )
    if "retrieval_ms" in metrics_aux:
        collector.stages[STAGE_RETRIEVAL] = metrics_aux["retrieval_ms"]
    if "generation_ms" in metrics_aux:
        collector.stages[STAGE_GENERATION] = metrics_aux["generation_ms"]
    rc = metrics_aux.get("retrieved_chunks")
    if isinstance(rc, int):
        collector.set_retrieved_chunks(rc)
    collector.set_token_usage(metrics_aux.get("token_usage"))

    collector.start_stage(STAGE_POSTPROCESS)
    _conf = 0.25 if response.get("guard_fallback") else 0.8
    db_question = Question(
        user_id=ctx.current_user.id,
        question_text=question,
        answer_text=response["answer"],
        source_documents=json.dumps(document_ids) if document_ids else None,
        confidence_score=_conf,
    )
    ctx.db.add(db_question)
    ctx.db.commit()
    ctx.db.refresh(db_question)

    doc_id_for_progress: Optional[int] = (
        document_ids[0] if document_ids else None
    )
    progress_service.record_question_asked(
        ctx.db, ctx.current_user.id, doc_id_for_progress
    )
    ctx.db.commit()
    collector.flush_stage()

    collector.emit(workflow="rag_qa", error=None)

    return RagAskResult(
        question_id=db_question.id,
        question=question,
        answer=response["answer"],
        sources=response["sources"],
        confidence_score=db_question.confidence_score,
    )
