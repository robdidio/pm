from fastapi import HTTPException

from app import db
from app.models import BoardPayload


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
