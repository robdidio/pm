import type { BoardData, Card, Column } from "@/lib/kanban";
import { toCardId, toColumnId } from "@/lib/kanban";

type BoardResponse = {
    board: { id: string; title: string };
    columns: Array<Column & { position?: number } & { cardIds: string[] }>;
    cards: Record<string, Card>;
};

type ApiOptions = {
    username?: string;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "";

const apiFetch = async <T>(
    path: string,
    options: RequestInit = {},
    apiOptions: ApiOptions = {}
): Promise<T> => {
    const headers = new Headers(options.headers);
    headers.set("Content-Type", "application/json");
    if (apiOptions.username) {
        headers.set("X-User", apiOptions.username);
    }

    const response = await fetch(`${apiBase}${path}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Request failed");
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return (await response.json()) as T;
};

export const toBoardData = (payload: BoardResponse): BoardData => {
    const cards: Record<string, Card> = Object.fromEntries(
        Object.entries(payload.cards).map(([id, card]) => [
            toCardId(id),
            { ...card, id: toCardId(card.id) },
        ])
    );

    return {
        columns: payload.columns.map((column) => ({
            id: toColumnId(column.id),
            title: column.title,
            cardIds: column.cardIds.map((cardId) => toCardId(cardId)),
        })),
        cards,
    };
};

export const fetchBoard = (username?: string) =>
    apiFetch<BoardResponse>("/api/board", {}, { username });

export const updateColumn = (
    columnId: number,
    payload: { title?: string; position?: number },
    username?: string
) =>
    apiFetch(`/api/columns/${columnId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    }, { username });

export const createCard = (
    payload: { column_id: number; title: string; details: string; position?: number },
    username?: string
) =>
    apiFetch<{ id: string }>("/api/cards", {
        method: "POST",
        body: JSON.stringify(payload),
    }, { username });

export const updateCard = (
    cardId: number,
    payload: { title?: string; details?: string; column_id?: number; position?: number },
    username?: string
) =>
    apiFetch(`/api/cards/${cardId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
    }, { username });

export const deleteCard = (cardId: number, username?: string) =>
    apiFetch(`/api/cards/${cardId}`, { method: "DELETE" }, { username });
