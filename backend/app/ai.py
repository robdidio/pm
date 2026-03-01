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
        raise HTTPException(status_code=502, detail="upstream_error")

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
        "CRITICAL: Use the EXACT column and card IDs from the board context below - do NOT invent new IDs. "
        "Return exactly this schema with double-quoted keys: "
        '{"schemaVersion": 1, "board": {"columns": [{"id": "col-xxx", "title": "Name", "cardIds": ["card-yyy"]}], "cards": {"card-yyy": {"id": "card-yyy", "title": "Name", "details": "Text"}}}, "operations": [...], "assistantMessage": "..."} '
        "Include a full board replacement and an operations list. "
        "If no changes are needed, return the current board and an empty operations array. "
        "If the user asks for a summary or non-board update, you MUST include assistantMessage with the reply,"
        " keep the board unchanged, and set operations to an empty array. "
        "Use schemaVersion 1. "
        "Operation field names (use exactly these): "
        "create_card(card: {id, title, details}, columnId, position), "
        "update_card(cardId, title, details), "
        "move_card(cardId, columnId, position), "
        "delete_card(cardId), "
        "rename_column(columnId, title). "
        "IMPORTANT: The cards object must have BOTH the id key and the card-id as dictionary key for each card. "
        "Example card entry: 'card-1': {'id': 'card-1', 'title': 'My card', 'details': 'Description'} "
        "Ensure every cardId in columns.cardIds exists in cards as a dictionary key. "
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
    logger.debug("AI raw response: %s", raw[:2000])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("AI response is not valid JSON: %s", raw[:200])
        raise HTTPException(status_code=502, detail="openrouter_invalid_json") from exc

    if "board" not in data:
        logger.warning("AI response missing 'board' key")
        raise HTTPException(status_code=502, detail="openrouter_invalid_schema")

    board_data = data["board"]

    if "columns" not in board_data:
        logger.warning("AI response missing 'board.columns'")
        raise HTTPException(status_code=502, detail="openrouter_invalid_schema")

    if "cards" not in board_data:
        logger.warning("AI response missing 'board.cards'")
        raise HTTPException(status_code=502, detail="openrouter_invalid_schema")

    cards = board_data["cards"]
    for card_id, card_data in cards.items():
        if not isinstance(card_data, dict):
            logger.warning("AI response: card %s is not a dict", card_id)
            raise HTTPException(status_code=502, detail="openrouter_invalid_schema")
        if "id" not in card_data:
            logger.warning("AI response: card %s missing 'id' field", card_id)
            raise HTTPException(status_code=502, detail="openrouter_invalid_schema")
        if card_data["id"] != card_id:
            logger.warning(
                "AI response: card key %r has mismatched 'id' field %r",
                card_id, card_data["id"],
            )
            raise HTTPException(status_code=502, detail="openrouter_invalid_schema")

    for column in board_data["columns"]:
        for ref_id in column.get("cardIds", []):
            if ref_id not in cards:
                logger.warning(
                    "AI response: column %r references unknown cardId %r",
                    column.get("id"), ref_id,
                )
                raise HTTPException(status_code=502, detail="openrouter_invalid_schema")

    try:
        parsed = AiBoardResponse.model_validate(data)
    except ValidationError as exc:
        logger.warning("OpenRouter invalid schema response: %s", raw[:500])
        logger.warning("Validation error: %s", exc)
        raise HTTPException(status_code=502, detail="openrouter_invalid_schema") from exc

    if parsed.schemaVersion != 1:
        raise HTTPException(status_code=502, detail="openrouter_schema_version_mismatch")

    return parsed
