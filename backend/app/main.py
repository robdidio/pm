import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from app import db
from app.auth import SECURE_COOKIES
from app.config import get_db_path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

logger = logging.getLogger("pm.main")

_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self';"
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not SECURE_COOKIES:
        logger.warning(
            "SECURE_COOKIES is not set; session cookies will not be marked Secure. "
            "Set SECURE_COOKIES=true for HTTPS deployments."
        )
    db.init_db(get_db_path())
    yield


app = FastAPI(lifespan=lifespan)

from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.board import router as board_router  # noqa: E402
from app.routes.ai import router as ai_router  # noqa: E402

app.include_router(auth_router)
app.include_router(board_router)
app.include_router(ai_router)

@app.middleware("http")
async def security_headers(request: Request, call_next: Callable) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = _CSP
    return response


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
