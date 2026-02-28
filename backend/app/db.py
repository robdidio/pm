from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ColumnInput:
    id: str
    title: str
    position: int


@dataclass(frozen=True)
class CardInput:
    id: str
    column_id: str
    title: str
    details: str
    position: int


DEFAULT_USER_ID = "user"
DEFAULT_BOARD_ID = "board-1"
DEFAULT_BOARD_TITLE = "My Board"

# NOTE: This seed data mirrors frontend/src/lib/kanban.ts initialData.
# If you change cards or columns here, update kanban.ts to match.
DEFAULT_COLUMNS = [
    ColumnInput("col-backlog", "Backlog", 0),
    ColumnInput("col-discovery", "Discovery", 1),
    ColumnInput("col-progress", "In Progress", 2),
    ColumnInput("col-review", "Review", 3),
    ColumnInput("col-done", "Done", 4),
]

DEFAULT_CARDS = [
    CardInput(
        "card-1",
        "col-backlog",
        "Align roadmap themes",
        "Draft quarterly themes with impact statements and metrics.",
        0,
    ),
    CardInput(
        "card-2",
        "col-backlog",
        "Gather customer signals",
        "Review support tags, sales notes, and churn feedback.",
        1,
    ),
    CardInput(
        "card-3",
        "col-discovery",
        "Prototype analytics view",
        "Sketch initial dashboard layout and key drill-downs.",
        0,
    ),
    CardInput(
        "card-4",
        "col-progress",
        "Refine status language",
        "Standardize column labels and tone across the board.",
        0,
    ),
    CardInput(
        "card-5",
        "col-progress",
        "Design card layout",
        "Add hierarchy and spacing for scanning dense lists.",
        1,
    ),
    CardInput(
        "card-6",
        "col-review",
        "QA micro-interactions",
        "Verify hover, focus, and loading states.",
        0,
    ),
    CardInput(
        "card-7",
        "col-done",
        "Ship marketing page",
        "Final copy approved and asset pack delivered.",
        0,
    ),
    CardInput(
        "card-8",
        "col-done",
        "Close onboarding sprint",
        "Document release notes and share internally.",
        1,
    ),
]


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT UNIQUE NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boards (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              title TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS columns (
              id TEXT PRIMARY KEY,
              board_id TEXT NOT NULL,
              title TEXT NOT NULL,
              position INTEGER NOT NULL,
              FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cards (
              id TEXT PRIMARY KEY,
              board_id TEXT NOT NULL,
              column_id TEXT NOT NULL,
              title TEXT NOT NULL,
              details TEXT NOT NULL,
              position INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
              FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id);
            CREATE INDEX IF NOT EXISTS idx_columns_board_id ON columns(board_id);
            CREATE INDEX IF NOT EXISTS idx_columns_board_position ON columns(board_id, position);
            CREATE INDEX IF NOT EXISTS idx_cards_board_id ON cards(board_id);
            CREATE INDEX IF NOT EXISTS idx_cards_column_position ON cards(column_id, position);
            """
        )

        existing_user = conn.execute(
            "SELECT id FROM users WHERE id = ?",
            (DEFAULT_USER_ID,),
        ).fetchone()
        if existing_user:
            return

        now = utc_now()
        conn.execute(
            "INSERT INTO users (id, username, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, "user", now),
        )
        conn.execute(
            "INSERT INTO boards (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (DEFAULT_BOARD_ID, DEFAULT_USER_ID, DEFAULT_BOARD_TITLE, now, now),
        )
        seed_board(conn, DEFAULT_BOARD_ID)


def seed_board(conn: sqlite3.Connection, board_id: str) -> None:
    conn.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))

    for column in DEFAULT_COLUMNS:
        conn.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (column.id, board_id, column.title, column.position),
        )

    now = utc_now()
    for card in DEFAULT_CARDS:
        conn.execute(
            """
            INSERT INTO cards (id, board_id, column_id, title, details, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card.id,
                board_id,
                card.column_id,
                card.title,
                card.details,
                card.position,
                now,
                now,
            ),
        )


def fetch_board(conn: sqlite3.Connection, board_id: str) -> dict[str, object]:
    columns_rows = conn.execute(
        "SELECT id, title, position FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    cards_rows = conn.execute(
        """
        SELECT id, column_id, title, details, position
        FROM cards
        WHERE board_id = ?
        ORDER BY column_id, position
        """,
        (board_id,),
    ).fetchall()

    cards_by_id: dict[str, dict[str, str]] = {}
    cards_by_column: dict[str, list[sqlite3.Row]] = {}
    for row in cards_rows:
        cards_by_id[row["id"]] = {
            "id": row["id"],
            "title": row["title"],
            "details": row["details"],
        }
        cards_by_column.setdefault(row["column_id"], []).append(row)

    columns: list[dict[str, object]] = []
    for row in columns_rows:
        column_cards = cards_by_column.get(row["id"], [])
        columns.append(
            {
                "id": row["id"],
                "title": row["title"],
                "cardIds": [card["id"] for card in column_cards],
            }
        )

    return {"columns": columns, "cards": cards_by_id}


def replace_board(
    conn: sqlite3.Connection,
    board_id: str,
    columns: Iterable[ColumnInput],
    cards: Iterable[CardInput],
) -> None:
    """Replace all board data atomically. Must be called within a `with conn:` block."""
    # Preserve creation timestamps so they survive full-board replacements.
    existing_created: dict[str, str] = {
        row["id"]: row["created_at"]
        for row in conn.execute(
            "SELECT id, created_at FROM cards WHERE board_id = ?", (board_id,)
        ).fetchall()
    }

    conn.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))

    for column in columns:
        conn.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (column.id, board_id, column.title, column.position),
        )

    now = utc_now()
    for card in cards:
        created_at = existing_created.get(card.id, now)
        conn.execute(
            """
            INSERT INTO cards (id, board_id, column_id, title, details, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card.id,
                board_id,
                card.column_id,
                card.title,
                card.details,
                card.position,
                created_at,
                now,
            ),
        )

    conn.execute(
        "UPDATE boards SET updated_at = ? WHERE id = ?",
        (now, board_id),
    )
