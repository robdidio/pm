from fastapi.testclient import TestClient

from app.main import AUTH_COOKIE_NAME, app


def test_auth_status_unauthenticated() -> None:
    client = TestClient(app)
    response = client.get("/api/auth/status")

    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_login_sets_cookie_and_status_true() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )

    assert response.status_code == 200
    assert response.cookies.get(AUTH_COOKIE_NAME) is not None

    status_response = client.get("/api/auth/status")
    assert status_response.json() == {"authenticated": True}


def test_login_rejects_invalid_credentials() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "wrong"},
    )

    assert response.status_code == 401


def test_logout_clears_cookie() -> None:
    client = TestClient(app)
    client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )

    response = client.post("/api/auth/logout")
    assert response.status_code == 200

    status_response = client.get("/api/auth/status")
    assert status_response.json() == {"authenticated": False}
