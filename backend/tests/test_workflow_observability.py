"""Workflow metrics: percentiles, ring buffer, collector emit shape."""

from __future__ import annotations

import json
import logging

import pytest

from app.observability.workflow_metrics import (
    STAGE_NORMALIZE,
    STAGE_TOTAL,
    WorkflowMetricsCollector,
    WorkflowMetricsStore,
    average,
    percentile_nearest_rank,
)


def test_average():
    assert average([]) == 0.0
    assert average([10.0, 20.0, 30.0]) == 20.0


def test_percentile_nearest_rank():
    xs = [10.0, 20.0, 30.0, 40.0, 100.0]
    assert percentile_nearest_rank(xs, 50) == 30.0
    assert percentile_nearest_rank(xs, 95) == 100.0
    assert percentile_nearest_rank(xs, 100) == 100.0


def test_ring_buffer_drops_oldest():
    s = WorkflowMetricsStore(maxlen=3)
    for i in range(5):
        s.record({"workflow": "t", STAGE_TOTAL: float(i)})
    snap = s.snapshot()
    assert len(snap) == 3
    assert snap[0][STAGE_TOTAL] == 2.0
    assert snap[-1][STAGE_TOTAL] == 4.0


def test_summary_by_workflow():
    s = WorkflowMetricsStore(maxlen=100)
    for i in range(10):
        s.record(
            {
                "workflow": "rag_qa",
                "stages": {STAGE_NORMALIZE: 1.0, "retrieval_ms": float(i)},
                STAGE_TOTAL: 100.0 + i,
            }
        )
    summ = s.summary()
    assert summ["sample_count"] == 10
    rag = summ["by_workflow"]["rag_qa"]
    assert rag["total_ms"]["count"] == 10.0
    assert rag["total_ms"]["avg"] == pytest.approx(104.5, rel=1e-3)


def test_workflow_metrics_collector_emit_logs(caplog):
    caplog.set_level(logging.INFO, logger="edumate.workflow_metrics")
    c = WorkflowMetricsCollector(
        request_id="rid-1",
        user_id="user-1",
        document_id=42,
        request_start_perf=None,
    )
    c.start_stage(STAGE_NORMALIZE)
    c.flush_stage()
    c.emit(workflow="quiz_generation", error=None)
    records = [r for r in caplog.records if r.name == "edumate.workflow_metrics"]
    assert records
    line = records[-1].message
    data = json.loads(line)
    assert data["event"] == "workflow_complete"
    assert data["workflow"] == "quiz_generation"
    assert data["request_id"] == "rid-1"
    assert data["user_id"] == "user-1"
    assert data["document_id"] == 42
    assert "stages" in data
    assert STAGE_TOTAL in data["stages"]


def test_diagnostics_workflow_metrics_gated(monkeypatch):
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "enable_workflow_metrics_endpoint", False)
    client = TestClient(app)
    assert client.get("/api/v1/diagnostics/workflow-metrics").status_code == 404

    monkeypatch.setattr(settings, "enable_workflow_metrics_endpoint", True)
    monkeypatch.setattr(settings, "metrics_admin_key", "secret")
    assert client.get("/api/v1/diagnostics/workflow-metrics").status_code == 403
    r = client.get(
        "/api/v1/diagnostics/workflow-metrics",
        headers={"X-Admin-Metrics-Key": "secret"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "sample_count" in body
    assert "by_workflow" in body

    h = client.get(
        "/api/v1/diagnostics/workflow-metrics/health",
        headers={"X-Admin-Metrics-Key": "secret"},
    )
    assert h.status_code == 200
    assert h.json().get("buffer_ok") is True
