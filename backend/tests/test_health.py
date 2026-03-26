"""Health endpoints (no external services required when S3 verify is off)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health_live(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_health_ready(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "ok"
