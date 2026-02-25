import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY is not set",
)
def test_ai_test_endpoint() -> None:
    client = TestClient(app)
    login = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert login.status_code == 200

    response = client.post("/api/ai/test")
    assert response.status_code == 200
    payload = response.json()

    assert "response" in payload
    assert "4" in payload["response"]
