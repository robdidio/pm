import os
import secrets

from fastapi import HTTPException, Request

AUTH_COOKIE_NAME = "pm_session"
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "").lower() == "true"

# Per-process session store: maps random token -> authenticated.
# Sessions are cleared on server restart, which is acceptable for this MVP.
_active_sessions: set[str] = set()


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    return bool(token and token in _active_sessions)


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="unauthorized")


def get_credentials() -> tuple[str, str]:
    username = os.environ.get("PM_USERNAME")
    password = os.environ.get("PM_PASSWORD")
    if not username or not password:
        raise HTTPException(status_code=500, detail="server_misconfigured")
    return username, password


def create_session() -> str:
    token = secrets.token_hex(32)
    _active_sessions.add(token)
    return token


def invalidate_session(request: Request) -> None:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        _active_sessions.discard(token)
