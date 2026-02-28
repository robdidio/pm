import os
import secrets
import time

from fastapi import HTTPException, Request

AUTH_COOKIE_NAME = "pm_session"
SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "").lower() == "true"

# Sessions expire after 24 hours of inactivity.
SESSION_TTL = 24 * 60 * 60

# Per-process session store: maps random token -> creation timestamp (monotonic).
# Sessions are cleared on server restart, which is acceptable for this MVP.
_active_sessions: dict[str, float] = {}


def is_authenticated(request: Request) -> bool:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return False
    created_at = _active_sessions.get(token)
    if created_at is None:
        return False
    if time.monotonic() - created_at > SESSION_TTL:
        _active_sessions.pop(token, None)
        return False
    return True


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
    now = time.monotonic()
    # Opportunistically evict expired sessions on each new login.
    expired = [t for t, ts in _active_sessions.items() if now - ts > SESSION_TTL]
    for t in expired:
        del _active_sessions[t]
    token = secrets.token_hex(32)
    _active_sessions[token] = now
    return token


def invalidate_session(request: Request) -> None:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        _active_sessions.pop(token, None)
