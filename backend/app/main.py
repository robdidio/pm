from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import get_db_path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db(get_db_path())
    yield


app = FastAPI(lifespan=lifespan)

from app.routes.auth import router as auth_router  # noqa: E402
from app.routes.board import router as board_router  # noqa: E402
from app.routes.ai import router as ai_router  # noqa: E402

app.include_router(auth_router)
app.include_router(board_router)
app.include_router(ai_router)

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
