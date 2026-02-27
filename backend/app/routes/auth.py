import logging

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


@router.get("/api/auth/status")
def auth_status(request: Request) -> dict:
    return {"authenticated": is_authenticated(request)}


@router.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> dict:
    valid_username, valid_password = get_credentials()
    if payload.username != valid_username or payload.password != valid_password:
        logger.warning("Login failed: invalid credentials for username %r", payload.username)
        raise HTTPException(status_code=401, detail="invalid_credentials")

    token = create_session()
    logger.info("Login: session created for username %r", payload.username)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
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
