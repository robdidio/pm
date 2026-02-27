from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app import db
from app.ai import (
    build_ai_system_prompt,
    build_board_summary,
    call_openrouter_messages,
    is_summary_request,
    parse_ai_board_response,
)
from app.auth import require_auth
from app.board import build_board_inputs
from app.config import get_db_path
from app.models import AiBoardRequest, BoardPayload

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/ai/board")
def ai_board(payload: AiBoardRequest, request: Request) -> dict[str, Any]:
    require_auth(request)
    if not payload.messages:
        raise HTTPException(status_code=400, detail="missing_messages")

    with db.get_connection(get_db_path()) as conn:
        board = db.fetch_board(conn, db.DEFAULT_BOARD_ID)

    if is_summary_request(payload.messages):
        summary = build_board_summary(BoardPayload.model_validate(board))
        return {
            "schemaVersion": 1,
            "operations": [],
            "board": board,
            "assistantMessage": summary,
        }

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
