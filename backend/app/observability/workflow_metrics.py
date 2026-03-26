from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional

from app.config import settings
from app.observability.structured_log import log_workflow_event
from app import telemetry

# Stage keys used across workflows (interview-friendly names)
STAGE_REQUEST_HANDLING = "request_handling_ms"
STAGE_NORMALIZE = "normalize_validate_ms"
STAGE_CONTENT_LOAD = "content_load_ms"
STAGE_RETRIEVAL = "retrieval_ms"
STAGE_GENERATION = "generation_ms"
STAGE_POSTPROCESS = "postprocess_ms"
STAGE_TOTAL = "total_ms"


def average(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def percentile_nearest_rank(values: List[float], p: float) -> float:
    """
    Nearest-rank p-percentile (p in [0, 100]).
    Index: ceil(p/100 * n) - 1 (0-based), per plan.
    """
    if not values:
        return 0.0
    if p <= 0:
        return min(values)
    if p >= 100:
        return max(values)
    xs = sorted(values)
    n = len(xs)
    idx = int(math.ceil(p / 100.0 * n)) - 1
    idx = max(0, min(idx, n - 1))
    return xs[idx]


def _stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"count": 0, "avg": 0.0, "p95": 0.0, "max": 0.0}
    return {
        "count": float(len(values)),
        "avg": round(average(values), 4),
        "p95": round(percentile_nearest_rank(values, 95.0), 4),
        "max": round(max(values), 4),
    }


@dataclass
class WorkflowMetricsStore:
    """Thread-safe ring buffer of completed workflow metric records."""

    maxlen: int = 2000
    _lock: threading.Lock = field(default_factory=threading.Lock)
    last_emit_perf: Optional[float] = None
    _records: Deque[Dict[str, Any]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.maxlen = max(1, int(self.maxlen))
        self._records = deque(maxlen=self.maxlen)

    def configure_maxlen(self, maxlen: int) -> None:
        with self._lock:
            self.maxlen = max(1, int(maxlen))
            self._records = deque(self._records, maxlen=self.maxlen)

    def record(self, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._records.append(payload)
            self.last_emit_perf = time.perf_counter()

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._records)

    def summary(self) -> Dict[str, Any]:
        rows = self.snapshot()
        by_workflow: Dict[str, Any] = {}
        for row in rows:
            wf = row.get("workflow") or "unknown"
            if wf not in by_workflow:
                by_workflow[wf] = {"total_ms": [], "stages": {}}
            tot = row.get(STAGE_TOTAL)
            if isinstance(tot, (int, float)):
                by_workflow[wf]["total_ms"].append(float(tot))
            stages = row.get("stages") or {}
            if isinstance(stages, dict):
                for sk, sv in stages.items():
                    if not isinstance(sv, (int, float)):
                        continue
                    by_workflow[wf]["stages"].setdefault(sk, []).append(float(sv))

        out: Dict[str, Any] = {
            "sample_count": len(rows),
            "buffer_capacity": self.maxlen,
            "by_workflow": {},
        }
        for wf, data in by_workflow.items():
            out["by_workflow"][wf] = {
                "total_ms": _stats(data["total_ms"]),
                "stages": {
                    sk: _stats(vs) for sk, vs in data["stages"].items()
                },
            }
        return out

    def health(self) -> Dict[str, Any]:
        last = self.last_emit_perf
        age: Optional[float] = None
        if last is not None:
            age = round(time.perf_counter() - last, 4)
        return {
            "buffer_ok": True,
            "buffer_capacity": self.maxlen,
            "sample_count": len(self.snapshot()),
            "last_emit_age_sec": age,
        }


workflow_metrics_store = WorkflowMetricsStore()


def _wandb_numeric_flatten(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Scalars only for W&B (prefix workflow_)."""
    flat: Dict[str, Any] = {"workflow_event": True}
    wf = payload.get("workflow")
    if wf:
        flat["workflow_name"] = wf
    for key in (
        STAGE_TOTAL,
        STAGE_REQUEST_HANDLING,
        STAGE_NORMALIZE,
        STAGE_CONTENT_LOAD,
        STAGE_RETRIEVAL,
        STAGE_GENERATION,
        STAGE_POSTPROCESS,
    ):
        v = payload.get(key)
        if isinstance(v, (int, float)):
            flat[f"wf_{key}"] = float(v)
    e2e = payload.get("e2e_http_ms")
    if isinstance(e2e, (int, float)):
        flat["wf_e2e_http_ms"] = float(e2e)
    stages = payload.get("stages")
    if isinstance(stages, dict):
        for sk, sv in stages.items():
            if isinstance(sv, (int, float)):
                flat[f"wf_stage_{sk}"] = float(sv)
    tok = payload.get("token_usage")
    if isinstance(tok, dict):
        for tk, tv in tok.items():
            if isinstance(tv, (int, float)):
                flat[f"wf_tokens_{tk}"] = float(tv)
    rc = payload.get("retrieved_chunks")
    if isinstance(rc, (int, float)):
        flat["wf_retrieved_chunks"] = float(rc)
    doc = payload.get("document_id")
    if isinstance(doc, (int, float)):
        flat["wf_document_id"] = float(doc)
    return flat


@dataclass
class WorkflowMetricsCollector:
    """Per-request collector: stages + emit structured log + ring buffer + W&B."""

    request_id: Optional[str] = None
    user_id: Optional[str] = None
    workflow: Optional[str] = None
    document_id: Optional[int] = None
    document_ids: Optional[List[int]] = None
    request_start_perf: Optional[float] = None
    workflow_start_perf: float = field(default_factory=time.perf_counter)
    _stage_start: Optional[float] = None
    _stage_key: Optional[str] = None
    stages: Dict[str, float] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def request_handling_cut(self) -> None:
        if self.request_start_perf is None:
            return
        rh = (self.workflow_start_perf - self.request_start_perf) * 1000.0
        self.stages[STAGE_REQUEST_HANDLING] = round(rh, 4)

    def start_stage(self, logical_name: str) -> None:
        self.flush_stage()
        self._stage_key = logical_name
        self._stage_start = time.perf_counter()

    def flush_stage(self) -> None:
        if self._stage_key is None or self._stage_start is None:
            return
        elapsed = (time.perf_counter() - self._stage_start) * 1000.0
        self.stages[self._stage_key] = round(elapsed, 4)
        self._stage_key = None
        self._stage_start = None

    def set_retrieved_chunks(self, n: int) -> None:
        self.extra["retrieved_chunks"] = n

    def set_token_usage(self, usage: Optional[Dict[str, Any]]) -> None:
        if usage:
            self.extra["token_usage"] = usage

    def emit(self, *, workflow: str, error: Optional[str] = None) -> None:
        self.workflow = workflow
        self.flush_stage()
        total_ms = (time.perf_counter() - self.workflow_start_perf) * 1000.0
        self.stages[STAGE_TOTAL] = round(total_ms, 4)

        payload: Dict[str, Any] = {
            "event": "workflow_complete",
            "workflow": workflow,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "document_id": self.document_id,
            "document_ids": self.document_ids,
            "stages": dict(self.stages),
            STAGE_TOTAL: self.stages.get(STAGE_TOTAL),
            "error": error,
        }
        if self.request_start_perf is not None:
            payload["e2e_http_ms"] = round(
                (time.perf_counter() - self.request_start_perf) * 1000.0, 4
            )
        for k, v in self.extra.items():
            if v is not None:
                payload[k] = v

        log_workflow_event(payload)
        workflow_metrics_store.record(dict(payload))
        telemetry.log_metrics(_wandb_numeric_flatten(payload))


def get_workflow_metrics_store() -> WorkflowMetricsStore:
    store = workflow_metrics_store
    store.configure_maxlen(settings.workflow_metrics_max_samples)
    return store
