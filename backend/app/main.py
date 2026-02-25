from contextlib import asynccontextmanager
from pathlib import Path
import json
from typing import Annotated, Any, Literal, Union
import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
import httpx
from pydantic import BaseModel, Field, ValidationError

from app import db

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db(get_db_path())
    yield


app = FastAPI(lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_DB_PATH = Path("/app/data/pm.db")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"

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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class AiBoardRequest(BaseModel):
    messages: list[ChatMessage]


class AiOperationCreateCard(BaseModel):
    type: Literal["create_card"]
    card: CardPayload
    columnId: str
    position: int


class AiOperationUpdateCard(BaseModel):
    type: Literal["update_card"]
    cardId: str
    title: str
    details: str


class AiOperationMoveCard(BaseModel):
    type: Literal["move_card"]
    cardId: str
    columnId: str
    position: int


class AiOperationDeleteCard(BaseModel):
    type: Literal["delete_card"]
    cardId: str


class AiOperationRenameColumn(BaseModel):
    type: Literal["rename_column"]
    columnId: str
    title: str


AiOperation = Annotated[
    Union[
        AiOperationCreateCard,
        AiOperationUpdateCard,
        AiOperationMoveCard,
        AiOperationDeleteCard,
        AiOperationRenameColumn,
    ],
    Field(discriminator="type"),
]


class AiBoardResponse(BaseModel):
    schemaVersion: int
    board: BoardPayload
    operations: list[AiOperation]


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


def get_openrouter_key() -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="missing_openrouter_key")
    return api_key


def call_openrouter_messages(messages: list[dict[str, str]]) -> str:
    api_key = get_openrouter_key()
    payload = {
        "model": OPENROUTER_MODEL,
        "temperature": 0,
        "messages": messages,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=20) as client:
        response = client.post(OPENROUTER_URL, json=payload, headers=headers)

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502, detail=f"openrouter_error:{response.status_code}"
        )

    data = response.json()
    message = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not message:
        raise HTTPException(status_code=502, detail="openrouter_empty_response")
    return message


def call_openrouter(prompt: str) -> str:
    return call_openrouter_messages([
        {"role": "user", "content": prompt},
    ])


def build_board_inputs(
    payload: BoardPayload,
) -> tuple[list[db.ColumnInput], list[db.CardInput]]:
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

    return column_inputs, card_inputs


def build_ai_system_prompt(board: dict[str, Any]) -> str:
    board_json = json.dumps(board, ensure_ascii=True)
    schema_example = {
        "schemaVersion": 1,
        "board": {
            "columns": [
                {"id": "col-1", "title": "Todo", "cardIds": ["card-1"]},
            ],
            "cards": {
                "card-1": {"id": "card-1", "title": "Title", "details": "Details"},
            },
        },
        "operations": [
            {
                "type": "update_card",
                "cardId": "card-1",
                "title": "Title",
                "details": "Details",
            }
        ],
    }
    schema_json = json.dumps(schema_example, ensure_ascii=True)

    return (
        "You are a project management assistant. "
        "Return JSON only, no markdown or extra text. "
        "The response must include a full board replacement and an operations list. "
        "Use schemaVersion 1. "
        "Use unique string ids; for new cards prefer 'card-' prefix. "
        "Operations types: create_card, update_card, move_card, delete_card, rename_column. "
        f"Schema example: {schema_json} "
        f"Board context: {board_json}"
    )


def parse_ai_board_response(raw: str) -> AiBoardResponse:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise HTTPException(status_code=502, detail="openrouter_invalid_json")
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="openrouter_invalid_json") from exc

    try:
        parsed = AiBoardResponse.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail="openrouter_invalid_schema") from exc

    if parsed.schemaVersion != 1:
        raise HTTPException(status_code=502, detail="openrouter_schema_version_mismatch")

    return parsed


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
    column_inputs, card_inputs = build_board_inputs(payload)

    with db.get_connection(get_db_path()) as conn:
        db.replace_board(conn, db.DEFAULT_BOARD_ID, column_inputs, card_inputs)
        return db.fetch_board(conn, db.DEFAULT_BOARD_ID)


@app.post("/api/ai/board")
def ai_board(payload: AiBoardRequest, request: Request) -> dict[str, Any]:
    require_auth(request)
    if not payload.messages:
        raise HTTPException(status_code=400, detail="missing_messages")

    with db.get_connection(get_db_path()) as conn:
        board = db.fetch_board(conn, db.DEFAULT_BOARD_ID)

    system_prompt = build_ai_system_prompt(board)
    messages = [
        {"role": "system", "content": system_prompt},
        *(
            {"role": message.role, "content": message.content}
            for message in payload.messages
        ),
    ]

    response = call_openrouter_messages(messages)
    ai_response = parse_ai_board_response(response)
    column_inputs, card_inputs = build_board_inputs(ai_response.board)

    with db.get_connection(get_db_path()) as conn:
        db.replace_board(conn, db.DEFAULT_BOARD_ID, column_inputs, card_inputs)
        updated_board = db.fetch_board(conn, db.DEFAULT_BOARD_ID)

    return {
        "schemaVersion": ai_response.schemaVersion,
        "operations": ai_response.operations,
        "board": updated_board,
    }


@app.post("/api/ai/test")
def ai_test(request: Request) -> dict[str, str]:
    require_auth(request)
    response = call_openrouter("What is 2+2? Respond with a single number.")
    return {"response": response}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
