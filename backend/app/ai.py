import json
import logging
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import OPENROUTER_MODEL, OPENROUTER_URL, get_openrouter_key
from app.models import AiBoardResponse, BoardPayload, ChatMessage

logger = logging.getLogger("pm.ai")


def call_openrouter_messages(messages: list[dict[str, str]]) -> str:
    api_key = get_openrouter_key()
    payload = {
        "model": OPENROUTER_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
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
            },
            {
                "type": "move_card",
                "cardId": "card-1",
                "columnId": "col-1",
                "position": 0,
            },
        ],
        "assistantMessage": "Updated card-1 details.",
    }
    summary_example = {
        "schemaVersion": 1,
        "board": {
            "columns": [
                {"id": "col-1", "title": "Todo", "cardIds": ["card-1"]},
            ],
            "cards": {
                "card-1": {"id": "card-1", "title": "Title", "details": "Details"},
            },
        },
        "operations": [],
        "assistantMessage": "Summary: The board tracks planning, discovery, delivery, and QA work.",
    }
    schema_json = json.dumps(schema_example, ensure_ascii=True)
    summary_json = json.dumps(summary_example, ensure_ascii=True)

    return (
        "You are a project management assistant. "
        "Return a single JSON object only, no markdown or extra text. "
        "Return exactly this schema with double-quoted keys: "
        "{schemaVersion:1, board:{columns:[{id,title,cardIds}], cards:{[id]:{id,title,details}}}, operations:[...]} "
        "Include a full board replacement and an operations list. "
        "If no changes are needed, return the current board and an empty operations array. "
        "If the user asks for a summary or non-board update, you MUST include assistantMessage with the reply,"
        " keep the board unchanged, and set operations to an empty array. "
        "Use schemaVersion 1. "
        "Use unique string ids; for new cards prefer 'card-' prefix. "
        "Operation field names (use exactly these): "
        "create_card(card, columnId, position), "
        "update_card(cardId, title, details), "
        "move_card(cardId, columnId, position), "
        "delete_card(cardId), "
        "rename_column(columnId, title). "
        "Ensure every cardId in columns exists in cards. "
        f"Schema example: {schema_json} "
        f"Summary example: {summary_json} "
        f"Board context: {board_json}"
    )


def is_summary_request(messages: list[ChatMessage]) -> bool:
    for message in reversed(messages):
        if message.role != "user":
            continue
        content = message.content.lower()
        return "summarize" in content or "summary" in content
    return False


def build_board_summary(board: BoardPayload) -> str:
    total_cards = len(board.cards)
    lines = [f"Summary: {len(board.columns)} columns, {total_cards} cards."]

    for column in board.columns:
        titles = [
            board.cards[card_id].title
            for card_id in column.cardIds
            if card_id in board.cards
        ]
        if not titles:
            lines.append(f"{column.title} (0): No cards.")
            continue

        preview = "; ".join(titles[:3])
        if len(titles) > 3:
            preview = f"{preview}; ..."
        lines.append(f"{column.title} ({len(titles)}): {preview}")

    return "\n".join(lines)


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
        logger.warning("OpenRouter invalid schema response: %s", raw)
        raise HTTPException(status_code=502, detail="openrouter_invalid_schema") from exc

    if parsed.schemaVersion != 1:
        raise HTTPException(status_code=502, detail="openrouter_schema_version_mismatch")

    return parsed
