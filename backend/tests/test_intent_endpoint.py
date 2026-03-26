from __future__ import annotations

from fastapi.testclient import TestClient


def test_intent_endpoint_requires_auth():
    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/v1/ai/intent", json={"prompt": "hi"})
    assert resp.status_code in (401, 403)


