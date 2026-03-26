from __future__ import annotations

from app.database import Flashcard, FlashcardSet
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
from app.workflows.types import FlashcardGenInput, FlashcardGenResult, WorkflowContext


def run(ctx: WorkflowContext, inp: FlashcardGenInput) -> FlashcardGenResult:
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
    num_cards = (
        inp.num_cards
        if inp.num_cards is not None
        else ctx.settings.flashcards_default
    )
    if num_cards < 1 or num_cards > ctx.settings.flashcards_max:
        collector.flush_stage()
        raise ValidationError("num_cards out of bounds")
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
        flashcards = ctx.ai_service.generate_flashcards(
            content=loaded.text, num_cards=num_cards, metrics_out=metrics_aux
        )
    except ValueError as e:
        raise GuardrailError(str(e)) from e
    collector.set_token_usage(metrics_aux.get("token_usage"))
    collector.flush_stage()

    collector.start_stage(STAGE_POSTPROCESS)
    db_set = FlashcardSet(
        user_id=ctx.current_user.id,
        source_document_id=inp.document_id,
        title=f"Flashcards from Document {inp.document_id}",
        description=f"AI-generated set with {len(flashcards)} cards",
        card_count=len(flashcards),
    )
    ctx.db.add(db_set)
    ctx.db.commit()
    ctx.db.refresh(db_set)

    for card in flashcards:
        ctx.db.add(
            Flashcard(
                flashcard_set_id=db_set.id,
                front=card.get("front", ""),
                back=card.get("back", ""),
            )
        )
    ctx.db.commit()

    progress_service.record_flashcards_generated(
        ctx.db, ctx.current_user.id, inp.document_id, len(flashcards)
    )
    ctx.db.commit()
    collector.flush_stage()
    collector.emit(workflow="flashcard_generation", error=None)

    return FlashcardGenResult(
        flashcard_set_id=db_set.id,
        document_id=inp.document_id,
        flashcards=flashcards,
        total_cards=len(flashcards),
    )
