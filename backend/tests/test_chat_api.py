from fastapi.testclient import TestClient

from backend.app import main as main_module

client = TestClient(main_module.app)


def test_chat_missing_api_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    response = client.post("/api/chat", json={"message": "2+2"})
    assert response.status_code == 500
    assert response.json() == {"detail": "OPENROUTER_API_KEY not configured"}
