import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
import app.main as main_module
from app.main import app


def setup_test_db(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    app.state.db_path = db_path
    db.init_db(db_path)


def login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


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


def test_ai_board_endpoint_applies_update(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    ai_payload = {
        "schemaVersion": 1,
        "board": {
            "columns": [
                {"id": "col-1", "title": "Todo", "cardIds": ["card-1"]},
            ],
            "cards": {
                "card-1": {
                    "id": "card-1",
                    "title": "Updated title",
                    "details": "Updated details",
                }
            },
        },
        "operations": [
            {
                "type": "update_card",
                "cardId": "card-1",
                "title": "Updated title",
                "details": "Updated details",
            }
        ],
    }

    def fake_call_openrouter_messages(_: list[dict[str, str]]) -> str:
        return json.dumps(ai_payload)

    monkeypatch.setattr(main_module, "call_openrouter_messages", fake_call_openrouter_messages)

    response = client.post(
        "/api/ai/board",
        json={"messages": [{"role": "user", "content": "Update the card"}]},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["schemaVersion"] == 1
    assert payload["board"]["columns"][0]["title"] == "Todo"
    assert payload["board"]["cards"]["card-1"]["title"] == "Updated title"
    assert payload["operations"][0]["type"] == "update_card"


def test_ai_board_rejects_invalid_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    def fake_call_openrouter_messages(_: list[dict[str, str]]) -> str:
        return json.dumps({"schemaVersion": 1, "board": {"columns": [], "cards": {}}})

    monkeypatch.setattr(main_module, "call_openrouter_messages", fake_call_openrouter_messages)

    response = client.post(
        "/api/ai/board",
        json={"messages": [{"role": "user", "content": "Update the card"}]},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "openrouter_invalid_schema"
