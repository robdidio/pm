import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
import app.routes.ai as routes_ai
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

    monkeypatch.setattr(routes_ai, "call_openrouter_messages", fake_call_openrouter_messages)

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

    monkeypatch.setattr(routes_ai, "call_openrouter_messages", fake_call_openrouter_messages)

    response = client.post(
        "/api/ai/board",
        json={"messages": [{"role": "user", "content": "Update the card"}]},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "openrouter_invalid_schema"


def test_ai_board_move_card_with_toColumnId(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AI may use toColumnId instead of columnId for move_card — both must be accepted."""
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    ai_payload = {
        "schemaVersion": 1,
        "board": {
            "columns": [
                {"id": "col-1", "title": "Todo", "cardIds": []},
                {"id": "col-2", "title": "Done", "cardIds": ["card-1"]},
            ],
            "cards": {
                "card-1": {"id": "card-1", "title": "A card", "details": "Details"}
            },
        },
        "operations": [
            {
                "type": "move_card",
                "cardId": "card-1",
                "toColumnId": "col-2",
            }
        ],
    }

    def fake_call_openrouter_messages(_: list[dict[str, str]]) -> str:
        return json.dumps(ai_payload)

    monkeypatch.setattr(routes_ai, "call_openrouter_messages", fake_call_openrouter_messages)

    response = client.post(
        "/api/ai/board",
        json={"messages": [{"role": "user", "content": "Move card-1 to Done"}]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["operations"][0]["type"] == "move_card"
    done_col = next(c for c in payload["board"]["columns"] if c["id"] == "col-2")
    assert "card-1" in done_col["cardIds"]


def test_ai_board_summary_bypasses_ai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    def fake_call_openrouter_messages(_: list[dict[str, str]]) -> str:
        raise AssertionError("AI should not be called for summaries")

    monkeypatch.setattr(routes_ai, "call_openrouter_messages", fake_call_openrouter_messages)

    response = client.post(
        "/api/ai/board",
        json={"messages": [{"role": "user", "content": "Please summarize my project"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["operations"] == []
    assert payload["assistantMessage"].startswith("Summary:")
