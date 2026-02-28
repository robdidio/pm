import pytest


@pytest.fixture(autouse=True)
def credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required auth credentials for every test."""
    monkeypatch.setenv("PM_USERNAME", "user")
    monkeypatch.setenv("PM_PASSWORD", "password")


@pytest.fixture(autouse=True)
def reset_auth_state() -> None:
    """Clear in-process session and rate-limit state between tests."""
    import app.auth as auth_module
    import app.routes.ai as ai_routes_module
    import app.routes.auth as auth_routes_module

    auth_module._active_sessions.clear()
    auth_routes_module._login_attempts.clear()
    ai_routes_module._ai_request_times.clear()
