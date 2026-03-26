"""
Retrieval validation between search and generation (RAG).

Chroma/LangChain scores are distance-style: lower values mean closer matches for
typical L2/cosine distance configurations. Set rag_max_best_chunk_distance in
Settings to None to disable the distance check.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from langchain.schema import Document

logger = logging.getLogger("edumate.guards")


@dataclass(frozen=True)
class RetrievalAssessment:
    ok: bool
    reason: str = ""

    @property
    def is_failure(self) -> bool:
        return not self.ok


def assess_retrieval_for_generation(
    results: Sequence[Tuple[Document, float]],
    *,
    min_non_empty_chunks: int,
    min_total_chars: int,
    max_best_distance: float | None,
) -> RetrievalAssessment:
    nonempty = [
        (d, s)
        for d, s in results
        if d.page_content and d.page_content.strip()
    ]
    if len(nonempty) < min_non_empty_chunks:
        logger.warning(
            "guard_fallback retrieval reason=too_few_chunks chunks=%s min=%s",
            len(nonempty),
            min_non_empty_chunks,
        )
        return RetrievalAssessment(False, "too_few_chunks")

    total_chars = sum(len(d.page_content or "") for d, _ in nonempty)
    if total_chars < min_total_chars:
        logger.warning(
            "guard_fallback retrieval reason=context_too_short chars=%s min=%s",
            total_chars,
            min_total_chars,
        )
        return RetrievalAssessment(False, "context_too_short")

    if max_best_distance is not None and nonempty:
        best = min(s for _, s in nonempty)
        if best > max_best_distance:
            logger.warning(
                "guard_fallback retrieval reason=low_relevance best_distance=%.4f max=%.4f",
                best,
                max_best_distance,
            )
            return RetrievalAssessment(False, "low_relevance")

    return RetrievalAssessment(True, "")


def documents_from_results(results: List[Tuple[Document, float]]) -> List[Document]:
    return [d for d, _ in results]
