import pytest


@pytest.fixture(autouse=True)
def credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required auth credentials for every test."""
    monkeypatch.setenv("PM_USERNAME", "user")
    monkeypatch.setenv("PM_PASSWORD", "password")
