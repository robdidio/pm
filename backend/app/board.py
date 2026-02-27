import logging

from fastapi import HTTPException

from app import db
from app.models import BoardPayload

logger = logging.getLogger("pm.board")


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
                logger.warning("Board validation failed: card %r in column %r not found in cards dict", card_id, column.id)
                raise HTTPException(status_code=400, detail="invalid_board")
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
        logger.warning("Board validation failed: cards in payload not referenced by any column: %r", extra_cards)
        raise HTTPException(status_code=400, detail="invalid_board")

    return column_inputs, card_inputs
