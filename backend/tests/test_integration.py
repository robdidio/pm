import os

import httpx
import pytest

BASE_URL = os.getenv("PM_BASE_URL", "")


def _can_run() -> bool:
    return bool(BASE_URL)


def _can_run_openrouter() -> bool:
    return bool(BASE_URL) and bool(os.getenv("OPENROUTER_API_KEY"))


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_health() -> None:
    response = httpx.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_root() -> None:
    response = httpx.get(f"{BASE_URL}/", timeout=5)
    assert response.status_code == 200
    assert "Welcome back" in response.text


@pytest.mark.skipif(not _can_run_openrouter(), reason="PM_BASE_URL or OPENROUTER_API_KEY not set")
def test_live_chat_openrouter() -> None:
    response = httpx.post(
        f"{BASE_URL}/api/chat",
        json={"message": "What is 2+2? Reply with only the number."},
        timeout=30,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "response" in payload
    assert "4" in payload["response"]
