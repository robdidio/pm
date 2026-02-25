from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

AUTH_COOKIE_NAME = "pm_session"
AUTH_COOKIE_VALUE = "authenticated"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"


class LoginRequest(BaseModel):
    username: str
    password: str


def is_authenticated(request: Request) -> bool:
    return request.cookies.get(AUTH_COOKIE_NAME) == AUTH_COOKIE_VALUE


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/status")
def auth_status(request: Request) -> dict[str, bool]:
    return {"authenticated": is_authenticated(request)}


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> dict[str, str]:
    if payload.username != VALID_USERNAME or payload.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=AUTH_COOKIE_VALUE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return {"status": "ok"}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    return {"status": "ok"}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
