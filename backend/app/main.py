from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import db

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db(get_db_path())
    yield


app = FastAPI(lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_DB_PATH = Path("/app/data/pm.db")

AUTH_COOKIE_NAME = "pm_session"
AUTH_COOKIE_VALUE = "authenticated"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"


class LoginRequest(BaseModel):
    username: str
    password: str


class CardPayload(BaseModel):
    id: str
    title: str
    details: str


class ColumnPayload(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardPayload(BaseModel):
    columns: list[ColumnPayload]
    cards: dict[str, CardPayload]


def is_authenticated(request: Request) -> bool:
    return request.cookies.get(AUTH_COOKIE_NAME) == AUTH_COOKIE_VALUE


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="unauthorized")


def get_db_path() -> Path:
    if hasattr(app.state, "db_path"):
        return Path(app.state.db_path)
    env_path = os.environ.get("PM_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


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


@app.get("/api/board")
def get_board(request: Request) -> dict[str, Any]:
    require_auth(request)
    with db.get_connection(get_db_path()) as conn:
        return db.fetch_board(conn, db.DEFAULT_BOARD_ID)


@app.put("/api/board")
def update_board(payload: BoardPayload, request: Request) -> dict[str, Any]:
    require_auth(request)

    card_ids = set(payload.cards.keys())
    column_inputs: list[db.ColumnInput] = []
    card_inputs: list[db.CardInput] = []

    for index, column in enumerate(payload.columns):
        column_inputs.append(
            db.ColumnInput(
                id=column.id,
                title=column.title,
                position=index,
                card_ids=list(column.cardIds),
            )
        )

        for position, card_id in enumerate(column.cardIds):
            if card_id not in card_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"missing_card:{card_id}",
                )
            card = payload.cards[card_id]
            card_inputs.append(
                db.CardInput(
                    id=card.id,
                    column_id=column.id,
                    title=card.title,
                    details=card.details,
                    position=position,
                )
            )

    if len(card_inputs) != len(card_ids):
        extra_cards = sorted(card_ids - {card.id for card in card_inputs})
        raise HTTPException(status_code=400, detail=f"unused_cards:{extra_cards}")

    with db.get_connection(get_db_path()) as conn:
        db.replace_board(conn, db.DEFAULT_BOARD_ID, column_inputs, card_inputs)
        return db.fetch_board(conn, db.DEFAULT_BOARD_ID)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
