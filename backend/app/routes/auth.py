import logging
import time

from fastapi import APIRouter, HTTPException, Request, Response

from app.auth import (
    AUTH_COOKIE_NAME,
    SECURE_COOKIES,
    create_session,
    get_credentials,
    invalidate_session,
    is_authenticated,
)
from app.models import LoginRequest

logger = logging.getLogger("pm.auth")

router = APIRouter()

# Max login attempts per IP per 60-second sliding window.
_LOGIN_RATE_LIMIT = 10
_LOGIN_RATE_WINDOW = 60.0
_login_attempts: dict[str, list[float]] = {}


def _check_login_rate_limit(ip: str) -> None:
    now = time.monotonic()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < _LOGIN_RATE_WINDOW]
    if len(attempts) >= _LOGIN_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="rate_limit_exceeded")
    attempts.append(now)
    _login_attempts[ip] = attempts


@router.get("/api/auth/status")
def auth_status(request: Request) -> dict:
    return {"authenticated": is_authenticated(request)}


@router.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)

    valid_username, valid_password = get_credentials()
    if payload.username != valid_username or payload.password != valid_password:
        logger.warning("Login failed: invalid credentials for username %r from %s", payload.username, client_ip)
        raise HTTPException(status_code=401, detail="invalid_credentials")

    token = create_session()
    logger.info("Login: session created for username %r", payload.username)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=SECURE_COOKIES,
        path="/",
    )
    return {"status": "ok"}


@router.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    invalidate_session(request)
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    logger.info("Logout: session invalidated")
    return {"status": "ok"}
