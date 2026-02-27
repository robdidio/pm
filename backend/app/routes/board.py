from typing import Any

from fastapi import APIRouter, Request

from app import db
from app.auth import require_auth
from app.board import build_board_inputs
from app.config import get_db_path
from app.models import BoardPayload

router = APIRouter()


@router.get("/api/board")
def get_board(request: Request) -> dict[str, Any]:
    require_auth(request)
    with db.get_connection(get_db_path()) as conn:
        return db.fetch_board(conn, db.DEFAULT_BOARD_ID)


@router.put("/api/board")
def update_board(payload: BoardPayload, request: Request) -> dict[str, Any]:
    require_auth(request)
    column_inputs, card_inputs = build_board_inputs(payload)

    with db.get_connection(get_db_path()) as conn:
        db.replace_board(conn, db.DEFAULT_BOARD_ID, column_inputs, card_inputs)
        return db.fetch_board(conn, db.DEFAULT_BOARD_ID)
