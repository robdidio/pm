"use client";

import { useEffect, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  pointerWithin,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { AIChatSidebar, type ChatMessage } from "@/components/AIChatSidebar";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";

const LOCAL_BOARD_KEY = "pm_local_board";

const cloneBoard = (board: BoardData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isAiSending, setIsAiSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const collisionDetectionStrategy = (args: Parameters<typeof closestCorners>[0]) => {
    const pointerCollisions = pointerWithin(args);
    if (pointerCollisions.length > 0) {
      return pointerCollisions;
    }
    return closestCorners(args);
  };

  const cardsById = board?.cards ?? {};

  const formatOperationsMessage = (operations: Array<{ type: string }>) => {
    if (operations.length === 0) {
      return "No changes were applied.";
    }

    const summary = operations
      .map((operation) => operation.type.replace(/_/g, " "))
      .join(", ");

    return `Applied ${operations.length} update(s): ${summary}.`;
  };

  useEffect(() => {
    let isActive = true;

    const loadBoard = async () => {
      setIsLoading(true);
      setErrorMessage(null);

      const stored = localStorage.getItem(LOCAL_BOARD_KEY);
      const localFallback = stored ? (JSON.parse(stored) as BoardData) : initialData;

      try {
        const response = await fetch("/api/board");
        if (response.ok) {
          const data = (await response.json()) as BoardData;
          if (isActive) {
            setBoard(data);
            localStorage.removeItem(LOCAL_BOARD_KEY);
          }
          return;
        }

        if (response.status === 404) {
          if (isActive) {
            setBoard(cloneBoard(localFallback));
          }
          return;
        }

        throw new Error("load_failed");
      } catch {
        if (isActive) {
          setBoard(cloneBoard(localFallback));
          setErrorMessage("Unable to reach the server. Working locally.");
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    loadBoard();

    return () => {
      isActive = false;
    };
  }, []);

  const persistBoard = async (nextBoard: BoardData) => {
    setIsSaving(true);
    setErrorMessage(null);

    try {
      const response = await fetch("/api/board", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nextBoard),
      });

      if (response.ok) {
        const data = (await response.json()) as BoardData;
        setBoard(data);
        localStorage.removeItem(LOCAL_BOARD_KEY);
        return;
      }

      if (response.status === 404) {
        localStorage.setItem(LOCAL_BOARD_KEY, JSON.stringify(nextBoard));
        return;
      }

      throw new Error("save_failed");
    } catch {
      localStorage.setItem(LOCAL_BOARD_KEY, JSON.stringify(nextBoard));
      setErrorMessage("Unable to save changes. Working locally.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id || !board) {
      return;
    }

    const nextBoard: BoardData = {
      ...board,
      columns: moveCard(board.columns, active.id as string, over.id as string),
    };
    setBoard(nextBoard);
    void persistBoard(nextBoard);
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!board) {
      return;
    }
    const nextBoard: BoardData = {
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    };
    setBoard(nextBoard);
    void persistBoard(nextBoard);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (!board) {
      return;
    }
    const id = createId("card");
    const nextBoard: BoardData = {
      ...board,
      cards: {
        ...board.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: board.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    };
    setBoard(nextBoard);
    void persistBoard(nextBoard);
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!board) {
      return;
    }
    const nextBoard: BoardData = {
      ...board,
      cards: Object.fromEntries(
        Object.entries(board.cards).filter(([id]) => id !== cardId)
      ),
      columns: board.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
          : column
      ),
    };
    setBoard(nextBoard);
    void persistBoard(nextBoard);
  };

  const handleSendAiPrompt = async () => {
    const trimmed = chatInput.trim();
    if (!trimmed || isAiSending) {
      return;
    }

    const userMessage: ChatMessage = {
      id: createId("msg"),
      role: "user",
      content: trimmed,
    };

    const nextMessages = [...chatMessages, userMessage];
    setChatMessages(nextMessages);
    setChatInput("");
    setIsAiSending(true);
    setChatError(null);

    let errorMsg: string | null = null;
    try {
      const response = await fetch("/api/ai/board", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: nextMessages.map((message) => ({
            role: message.role,
            content: message.content,
          })),
        }),
      });

      if (response.ok) {
        const data = (await response.json()) as {
          board: BoardData;
          operations: Array<{ type: string }>;
          assistantMessage?: string | null;
        };
        setBoard(data.board);
        localStorage.removeItem(LOCAL_BOARD_KEY);

        const reply = data.assistantMessage?.trim();
        const assistantMessage: ChatMessage = {
          id: createId("msg"),
          role: "assistant",
          content: reply && reply.length > 0
            ? reply
            : formatOperationsMessage(data.operations || []),
        };
        setChatMessages((current) => [...current, assistantMessage]);
        return;
      }

      if (response.status === 404) {
        errorMsg = "AI service is unavailable in local-only mode.";
        return;
      }

      let detailMessage: string | null = null;
      try {
        const errorPayload = (await response.json()) as { detail?: string };
        detailMessage = errorPayload.detail ?? null;
      } catch {
        detailMessage = null;
      }

      if (detailMessage === "openrouter_invalid_schema" || detailMessage === "invalid_board") {
        errorMsg = "AI response did not match the required schema. Try again.";
        return;
      }
      if (detailMessage === "openrouter_invalid_json") {
        errorMsg = "AI response was not valid JSON. Try again.";
        return;
      }
      if (detailMessage === "upstream_error") {
        errorMsg = "AI service returned an error. Try again.";
        return;
      }
      errorMsg = "Unable to reach the AI service. Please try again.";
    } catch {
      errorMsg = "Unable to reach the AI service. Please try again.";
    } finally {
      if (errorMsg !== null) {
        setChatMessages(chatMessages);
        setChatError(errorMsg);
      }
      setIsAiSending(false);
    }
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (isLoading || !board) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm font-semibold text-[var(--gray-text)]">
        Loading board...
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="flex flex-col gap-10">
            <header className="flex flex-col gap-4 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
              <div className="flex flex-wrap items-start justify-between gap-6">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                    Single Board Kanban
                  </p>
                  <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                    Kanban Studio
                  </h1>
                  <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                    Keep momentum visible. Rename columns, drag cards between stages,
                    and capture quick notes without getting buried in settings.
                  </p>
                  {isSaving ? (
                    <p className="mt-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)]">
                      Saving changes...
                    </p>
                  ) : null}
                  {errorMessage ? (
                    <p className="mt-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--secondary-purple)]">
                      {errorMessage}
                    </p>
                  ) : null}
                </div>
                <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                    Focus
                  </p>
                  <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                    One board. Five columns. Zero clutter.
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                {board.columns.map((column) => (
                  <div
                    key={column.id}
                    className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
                  >
                    <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                    {column.title}
                  </div>
                ))}
              </div>
            </header>

            <DndContext
              sensors={sensors}
              collisionDetection={collisionDetectionStrategy}
              onDragStart={handleDragStart}
              onDragEnd={handleDragEnd}
            >
              <section className="grid gap-6 lg:grid-cols-5">
                {board.columns.map((column) => (
                  <KanbanColumn
                    key={column.id}
                    column={column}
                    cards={column.cardIds.flatMap((cardId) => (board.cards[cardId] ? [board.cards[cardId]] : []))}
                    onRename={handleRenameColumn}
                    onAddCard={handleAddCard}
                    onDeleteCard={handleDeleteCard}
                  />
                ))}
              </section>
              <DragOverlay>
                {activeCard ? (
                  <div className="w-[260px]">
                    <KanbanCardPreview card={activeCard} />
                  </div>
                ) : null}
              </DragOverlay>
            </DndContext>
          </div>

          <AIChatSidebar
            messages={chatMessages}
            input={chatInput}
            isSending={isAiSending}
            errorMessage={chatError}
            onInputChange={setChatInput}
            onSend={handleSendAiPrompt}
          />
        </div>
      </main>
    </div>
  );
};
