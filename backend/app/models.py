from typing import Annotated, Literal, Union

from pydantic import AliasChoices, BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=1000)


class CardPayload(BaseModel):
    id: str
    title: str = Field(max_length=200)
    details: str = Field(max_length=10_000)


class ColumnPayload(BaseModel):
    id: str
    title: str = Field(max_length=100)
    cardIds: list[str] = Field(max_length=500)


class BoardPayload(BaseModel):
    columns: list[ColumnPayload] = Field(max_length=20)
    cards: Annotated[dict[str, CardPayload], Field(max_length=500)]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20_000)


class AiBoardRequest(BaseModel):
    messages: list[ChatMessage] = Field(max_length=200)


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
    cardId: str = Field(validation_alias=AliasChoices("cardId", "card_id"))
    columnId: str = Field(
        validation_alias=AliasChoices(
            "columnId", "toColumnId", "targetColumnId", "column_id", "to_column_id"
        )
    )
    position: int | None = None


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
    assistantMessage: str | None = None
