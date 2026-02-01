import os
import sqlite3
from pathlib import Path
from typing import Generator, Iterable

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(ENV_PATH)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "openai/gpt-oss-120b"


class ColumnCreate(BaseModel):
    title: str
    position: int | None = None


class ColumnUpdate(BaseModel):
    title: str | None = None
    position: int | None = None


class CardCreate(BaseModel):
    column_id: int
    title: str
    details: str = ""
    position: int | None = None


class CardUpdate(BaseModel):
    title: str | None = None
    details: str | None = None
    column_id: int | None = None
    position: int | None = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


DEFAULT_USER = "user"
DEFAULT_BOARD_TITLE = "My Board"
INITIAL_COLUMNS = [
    ("Backlog", [
        ("Align roadmap themes", "Draft quarterly themes with impact statements and metrics."),
        ("Gather customer signals", "Review support tags, sales notes, and churn feedback."),
    ]),
    ("Discovery", [
        ("Prototype analytics view", "Sketch initial dashboard layout and key drill-downs."),
    ]),
    ("In Progress", [
        ("Refine status language", "Standardize column labels and tone across the board."),
        ("Design card layout", "Add hierarchy and spacing for scanning dense lists."),
    ]),
    ("Review", [
        ("QA micro-interactions", "Verify hover, focus, and loading states."),
    ]),
    ("Done", [
        ("Ship marketing page", "Final copy approved and asset pack delivered."),
        ("Close onboarding sprint", "Document release notes and share internally."),
    ]),
]


def _resolve_static_dir() -> Path | None:
    env_dir = os.getenv("PM_STATIC_DIR", "").strip()
    candidates = [
        Path(env_dir) if env_dir else None,
        Path(__file__).resolve().parents[2] / "frontend" / "out",
        Path("/app/frontend/out"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def _get_db_path() -> Path:
    env_path = os.getenv("PM_DB_PATH", "").strip()
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[1] / "data" / "pm.db"


def _connect_db() -> sqlite3.Connection:
    db_path = _get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    conn = _connect_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'My Board',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE (user_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS columns (
            id INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id) REFERENCES boards(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY,
            column_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (column_id) REFERENCES columns(id)
        )
        """
    )
    conn.commit()
    conn.close()


def _mount_static_assets(static_dir: Path) -> None:
    next_assets = static_dir / "_next"
    if next_assets.exists():
        app.mount("/_next", StaticFiles(directory=next_assets), name="next-assets")
    static_assets = static_dir / "static"
    if static_assets.exists():
        app.mount("/static", StaticFiles(directory=static_assets), name="static-assets")


STATIC_DIR = _resolve_static_dir()

if STATIC_DIR:
    _mount_static_assets(STATIC_DIR)


def _get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _connect_db()
    try:
        yield conn
    finally:
        conn.close()


def _get_or_create_user(conn: sqlite3.Connection, username: str) -> int:
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute(
        "INSERT INTO users (username) VALUES (?)",
        (username,),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _get_or_create_board(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute(
        "INSERT INTO boards (user_id, title) VALUES (?, ?)",
        (user_id, DEFAULT_BOARD_TITLE),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _ensure_seed_data(conn: sqlite3.Connection, user_id: int) -> int:
    board_id = _get_or_create_board(conn, user_id)
    column_count = conn.execute(
        "SELECT COUNT(*) AS count FROM columns WHERE board_id = ?",
        (board_id,),
    ).fetchone()["count"]
    if column_count:
        return board_id

    for column_index, (column_title, cards) in enumerate(INITIAL_COLUMNS):
        column_cursor = conn.execute(
            "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
            (board_id, column_title, column_index),
        )
        column_id = int(column_cursor.lastrowid)
        for card_index, (title, details) in enumerate(cards):
            conn.execute(
                """
                INSERT INTO cards (column_id, title, details, position)
                VALUES (?, ?, ?, ?)
                """,
                (column_id, title, details, card_index),
            )
    conn.commit()
    return board_id


def _fetch_board(conn: sqlite3.Connection, user_id: int) -> dict:
    board_id = _ensure_seed_data(conn, user_id)
    board_row = conn.execute(
        "SELECT id, title FROM boards WHERE id = ?",
        (board_id,),
    ).fetchone()

    column_rows = conn.execute(
        "SELECT id, title, position FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    card_rows = conn.execute(
        """
        SELECT id, column_id, title, details, position
        FROM cards
        WHERE archived = 0 AND column_id IN (
            SELECT id FROM columns WHERE board_id = ?
        )
        ORDER BY column_id, position
        """,
        (board_id,),
    ).fetchall()

    cards_by_id = {
        str(row["id"]): {
            "id": str(row["id"]),
            "title": row["title"],
            "details": row["details"],
        }
        for row in card_rows
    }

    cards_by_column: dict[int, list[str]] = {int(row["id"]): [] for row in column_rows}
    for row in card_rows:
        cards_by_column[int(row["column_id"])].append(str(row["id"]))

    columns_payload = [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "position": row["position"],
            "cardIds": cards_by_column.get(int(row["id"]), []),
        }
        for row in column_rows
    ]

    return {
        "board": {"id": str(board_row["id"]), "title": board_row["title"]},
        "columns": columns_payload,
        "cards": cards_by_id,
    }


def _ordered_ids(rows: Iterable[sqlite3.Row]) -> list[int]:
    return [int(row["id"]) for row in rows]


def _resequence_positions(
    conn: sqlite3.Connection,
    table: str,
    ids: list[int],
    extra_where: str,
    extra_params: tuple,
) -> None:
    for index, item_id in enumerate(ids):
        conn.execute(
            f"UPDATE {table} SET position = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? {extra_where}",
            (index, item_id, *extra_params),
        )


def _get_username(x_user: str | None = Header(default=None)) -> str:
    return x_user or DEFAULT_USER


def _get_openrouter_api_key() -> str | None:
    return os.getenv("OPENROUTER_API_KEY")


def _call_openrouter(message: str) -> str:
    api_key = _get_openrouter_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": message}],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=20,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="OpenRouter request failed") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="OpenRouter returned an error")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise HTTPException(status_code=502, detail="OpenRouter response missing choices")
    message_data = choices[0].get("message")
    if not message_data or "content" not in message_data:
        raise HTTPException(status_code=502, detail="OpenRouter response missing content")
    return str(message_data["content"]).strip()


@app.on_event("startup")
def startup() -> None:
    _init_db()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/hello")
def hello() -> dict:
    return {"message": "Hello from FastAPI"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    response_text = _call_openrouter(payload.message)
    return ChatResponse(response=response_text)


@app.get("/api/board")
def get_board(
    username: str = Depends(_get_username),
    conn: sqlite3.Connection = Depends(_get_db),
) -> dict:
    user_id = _get_or_create_user(conn, username)
    return _fetch_board(conn, user_id)


@app.post("/api/columns")
def create_column(
    payload: ColumnCreate,
    username: str = Depends(_get_username),
    conn: sqlite3.Connection = Depends(_get_db),
) -> dict:
    user_id = _get_or_create_user(conn, username)
    board_id = _get_or_create_board(conn, user_id)

    columns = conn.execute(
        "SELECT id FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()
    ids = _ordered_ids(columns)

    insert_position = payload.position
    if insert_position is None or insert_position > len(ids):
        insert_position = len(ids)
    if insert_position < 0:
        insert_position = 0

    cursor = conn.execute(
        "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
        (board_id, payload.title, insert_position),
    )
    column_id = int(cursor.lastrowid)
    ids.insert(insert_position, column_id)
    _resequence_positions(conn, "columns", ids, "AND board_id = ?", (board_id,))
    conn.commit()

    return {"id": str(column_id)}


@app.patch("/api/columns/{column_id}")
def update_column(
    column_id: int,
    payload: ColumnUpdate,
    username: str = Depends(_get_username),
    conn: sqlite3.Connection = Depends(_get_db),
) -> dict:
    user_id = _get_or_create_user(conn, username)
    board_id = _get_or_create_board(conn, user_id)

    column = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    if payload.title is not None:
        conn.execute(
            "UPDATE columns SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.title, column_id),
        )

    if payload.position is not None:
        columns = conn.execute(
            "SELECT id FROM columns WHERE board_id = ? ORDER BY position",
            (board_id,),
        ).fetchall()
        ids = _ordered_ids(columns)
        if column_id in ids:
            ids.remove(column_id)
        insert_position = max(0, min(payload.position, len(ids)))
        ids.insert(insert_position, column_id)
        _resequence_positions(conn, "columns", ids, "AND board_id = ?", (board_id,))

    conn.commit()
    return {"status": "ok"}


@app.delete("/api/columns/{column_id}")
def delete_column(
    column_id: int,
    username: str = Depends(_get_username),
    conn: sqlite3.Connection = Depends(_get_db),
) -> dict:
    user_id = _get_or_create_user(conn, username)
    board_id = _get_or_create_board(conn, user_id)

    column = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, board_id),
    ).fetchone()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    conn.execute("DELETE FROM cards WHERE column_id = ?", (column_id,))
    conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))

    remaining = conn.execute(
        "SELECT id FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()
    _resequence_positions(conn, "columns", _ordered_ids(remaining), "AND board_id = ?", (board_id,))
    conn.commit()

    return {"status": "ok"}


@app.post("/api/cards")
def create_card(
    payload: CardCreate,
    username: str = Depends(_get_username),
    conn: sqlite3.Connection = Depends(_get_db),
) -> dict:
    user_id = _get_or_create_user(conn, username)
    board_id = _get_or_create_board(conn, user_id)

    column = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (payload.column_id, board_id),
    ).fetchone()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    cards = conn.execute(
        "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
        (payload.column_id,),
    ).fetchall()
    ids = _ordered_ids(cards)

    insert_position = payload.position
    if insert_position is None or insert_position > len(ids):
        insert_position = len(ids)
    if insert_position < 0:
        insert_position = 0

    cursor = conn.execute(
        """
        INSERT INTO cards (column_id, title, details, position)
        VALUES (?, ?, ?, ?)
        """,
        (payload.column_id, payload.title, payload.details, insert_position),
    )
    card_id = int(cursor.lastrowid)
    ids.insert(insert_position, card_id)
    _resequence_positions(conn, "cards", ids, "AND column_id = ?", (payload.column_id,))
    conn.commit()

    return {"id": str(card_id)}


@app.patch("/api/cards/{card_id}")
def update_card(
    card_id: int,
    payload: CardUpdate,
    username: str = Depends(_get_username),
    conn: sqlite3.Connection = Depends(_get_db),
) -> dict:
    user_id = _get_or_create_user(conn, username)
    board_id = _get_or_create_board(conn, user_id)

    card = conn.execute(
        """
        SELECT cards.id, cards.column_id
        FROM cards
        JOIN columns ON cards.column_id = columns.id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    if payload.title is not None:
        conn.execute(
            "UPDATE cards SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.title, card_id),
        )
    if payload.details is not None:
        conn.execute(
            "UPDATE cards SET details = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.details, card_id),
        )

    current_column_id = int(card["column_id"])
    target_column_id = payload.column_id or current_column_id

    if payload.column_id is not None:
        column = conn.execute(
            "SELECT id FROM columns WHERE id = ? AND board_id = ?",
            (payload.column_id, board_id),
        ).fetchone()
        if not column:
            raise HTTPException(status_code=404, detail="Column not found")

    if payload.position is not None or target_column_id != current_column_id:
        source_cards = conn.execute(
            "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
            (current_column_id,),
        ).fetchall()
        source_ids = _ordered_ids(source_cards)
        if card_id in source_ids:
            source_ids.remove(card_id)

        target_cards = conn.execute(
            "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
            (target_column_id,),
        ).fetchall()
        target_ids = _ordered_ids(target_cards)

        insert_position = payload.position
        if insert_position is None or insert_position > len(target_ids):
            insert_position = len(target_ids)
        if insert_position < 0:
            insert_position = 0

        target_ids.insert(insert_position, card_id)

        conn.execute(
            "UPDATE cards SET column_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (target_column_id, card_id),
        )
        _resequence_positions(conn, "cards", source_ids, "AND column_id = ?", (current_column_id,))
        _resequence_positions(conn, "cards", target_ids, "AND column_id = ?", (target_column_id,))

    conn.commit()
    return {"status": "ok"}


@app.delete("/api/cards/{card_id}")
def delete_card(
    card_id: int,
    username: str = Depends(_get_username),
    conn: sqlite3.Connection = Depends(_get_db),
) -> dict:
    user_id = _get_or_create_user(conn, username)
    board_id = _get_or_create_board(conn, user_id)

    card = conn.execute(
        """
        SELECT cards.id, cards.column_id
        FROM cards
        JOIN columns ON cards.column_id = columns.id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    column_id = int(card["column_id"])
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    remaining = conn.execute(
        "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
        (column_id,),
    ).fetchall()
    _resequence_positions(conn, "cards", _ordered_ids(remaining), "AND column_id = ?", (column_id,))
    conn.commit()
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root():
    if STATIC_DIR:
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

    return """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>PM MVP</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #032147; }
      h1 { margin-bottom: 8px; }
      p { color: #888888; }
      code { background: #f7f8fb; padding: 2px 6px; border-radius: 6px; }
    </style>
  </head>
  <body>
    <h1>Project Management MVP</h1>
    <p>FastAPI backend is running.</p>
    <p>Try <code>/api/hello</code> or <code>/health</code>.</p>
  </body>
</html>"""


@app.get("/{full_path:path}", include_in_schema=False)
def static_fallback(full_path: str):
    if not STATIC_DIR:
        return HTMLResponse("Not found", status_code=404)

    requested_path = STATIC_DIR / full_path
    if requested_path.is_dir():
        index_path = requested_path / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

    if requested_path.exists():
        return FileResponse(requested_path)

    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return HTMLResponse("Not found", status_code=404)
