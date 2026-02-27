from pathlib import Path

from fastapi.testclient import TestClient

from app import db
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


def test_get_board_requires_auth(tmp_path: Path) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)

    response = client.get("/api/board")
    assert response.status_code == 401


def test_get_board_returns_seed(tmp_path: Path) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    response = client.get("/api/board")
    assert response.status_code == 200
    payload = response.json()

    assert "columns" in payload
    assert "cards" in payload
    assert len(payload["columns"]) == 5


def test_update_board_missing_card_returns_generic_error(tmp_path: Path) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    payload = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": ["card-missing"]}],
        "cards": {},
    }
    response = client.put("/api/board", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_board"


def test_update_board_unused_card_returns_generic_error(tmp_path: Path) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    payload = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": []}],
        "cards": {"card-1": {"id": "card-1", "title": "Orphan", "details": "No column"}},
    }
    response = client.put("/api/board", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_board"


def test_update_board_title_too_long_returns_422(tmp_path: Path) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    payload = {
        "columns": [{"id": "col-1", "title": "Todo", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "x" * 201, "details": "ok"}},
    }
    response = client.put("/api/board", json=payload)
    assert response.status_code == 422


def test_update_board(tmp_path: Path) -> None:
    setup_test_db(tmp_path)
    client = TestClient(app)
    login(client)

    update_payload = {
        "columns": [
            {"id": "col-1", "title": "Todo", "cardIds": ["card-1"]},
            {"id": "col-2", "title": "Done", "cardIds": []},
        ],
        "cards": {"card-1": {"id": "card-1", "title": "Test", "details": "Ok"}},
    }

    response = client.put("/api/board", json=update_payload)
    assert response.status_code == 200

    follow_up = client.get("/api/board")
    assert follow_up.status_code == 200
    payload = follow_up.json()

    assert payload["columns"][0]["title"] == "Todo"
    assert payload["columns"][0]["cardIds"] == ["card-1"]
    assert payload["cards"]["card-1"]["title"] == "Test"
