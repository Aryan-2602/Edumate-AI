"""Opt-in diagnostics for workflow latency summaries (dev / interviews)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.observability.workflow_metrics import get_workflow_metrics_store

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _require_metrics_access(request: Request) -> None:
    if not settings.enable_workflow_metrics_endpoint:
        raise HTTPException(status_code=404, detail="Not found")
    expected = settings.metrics_admin_key
    if expected:
        if request.headers.get("X-Admin-Metrics-Key") != expected:
            raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/workflow-metrics")
async def workflow_metrics_summary(request: Request):
    """Aggregated avg / p95 / max from the in-memory ring buffer."""
    _require_metrics_access(request)
    store = get_workflow_metrics_store()
    return store.summary()


@router.get("/workflow-metrics/health")
async def workflow_metrics_health(request: Request):
    """Basic buffer health and time since last completed workflow."""
    _require_metrics_access(request)
    store = get_workflow_metrics_store()
    return store.health()
