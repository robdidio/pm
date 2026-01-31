"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type SetStateAction,
} from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { fetchBoard, createCard, deleteCard, toBoardData, updateCard, updateColumn } from "@/lib/api";
import { findCardLocation, fromCardId, fromColumnId, type BoardData } from "@/lib/kanban";

const CREDENTIALS = { username: "user", password: "password" };

export default function Home() {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState<string>(CREDENTIALS.username);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [boardError, setBoardError] = useState<string | null>(null);

  const refreshBoard = useCallback(async () => {
    setIsLoading(true);
    setBoardError(null);
    try {
      const payload = await fetchBoard(username);
      setBoard(toBoardData(payload));
    } catch (err) {
      setBoardError("Unable to load the board from the server.");
    } finally {
      setIsLoading(false);
    }
  }, [username]);

  const handleBoardChange = useCallback(
    (updater: SetStateAction<BoardData>) => {
      setBoard((prev) => {
        if (!prev) {
          return prev;
        }
        return typeof updater === "function" ? updater(prev) : updater;
      });
    },
    []
  );

  const handleLogin = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const username = String(formData.get("username") || "").trim();
    const password = String(formData.get("password") || "").trim();

    if (username === CREDENTIALS.username && password === CREDENTIALS.password) {
      setUsername(username);
      setIsAuthenticated(true);
      setError(null);
      event.currentTarget.reset();
      return;
    }

    setError("Incorrect username or password.");
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setBoard(null);
    setBoardError(null);
  };

  useEffect(() => {
    if (isAuthenticated) {
      refreshBoard();
    }
  }, [isAuthenticated, refreshBoard]);

  const handleRenameColumn = async (columnId: string, title: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to save column changes.");
      return;
    }
    try {
      await updateColumn(columnIdNumber, { title }, username);
    } catch (err) {
      setBoardError("Unable to save column changes.");
      refreshBoard();
    }
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    const columnIdNumber = Number(fromColumnId(columnId));
    if (Number.isNaN(columnIdNumber)) {
      setBoardError("Unable to add the card.");
      return;
    }
    try {
      await createCard(
        {
          column_id: columnIdNumber,
          title,
          details: details || "No details yet.",
        },
        username
      );
      refreshBoard();
    } catch (err) {
      setBoardError("Unable to add the card.");
      refreshBoard();
    }
  };

  const handleDeleteCard = async (columnId: string, cardId: string) => {
    const cardIdNumber = Number(fromCardId(cardId));
    if (Number.isNaN(cardIdNumber)) {
      return;
    }
    try {
      await deleteCard(cardIdNumber, username);
      refreshBoard();
    } catch (err) {
      setBoardError("Unable to remove the card.");
      refreshBoard();
    }
  };

  const handleMoveCard = async (
    activeId: string,
    _overId: string,
    nextColumns: BoardData["columns"]
  ) => {
    const location = findCardLocation(nextColumns, activeId);
    if (!location) {
      return;
    }
    const cardIdNumber = Number(fromCardId(activeId));
    const columnIdNumber = Number(fromColumnId(location.columnId));
    if (Number.isNaN(cardIdNumber) || Number.isNaN(columnIdNumber)) {
      return;
    }
    try {
      await updateCard(
        cardIdNumber,
        {
          column_id: columnIdNumber,
          position: location.index,
        },
        username
      );
      refreshBoard();
    } catch (err) {
      setBoardError("Unable to move the card.");
      refreshBoard();
    }
  };

  const welcomeCopy = useMemo(
    () =>
      "Sign in to continue to your Kanban board. Use the demo credentials to explore the MVP.",
    []
  );

  if (!isAuthenticated) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

        <main className="relative mx-auto flex min-h-screen max-w-xl items-center px-6 py-16">
          <section className="w-full rounded-[32px] border border-[var(--stroke)] bg-white/90 p-8 shadow-[var(--shadow)] backdrop-blur">
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
              Project Management MVP
            </p>
            <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
              Welcome back
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
              {welcomeCopy}
            </p>

            <form onSubmit={handleLogin} className="mt-6 space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  Username
                </label>
                <input
                  name="username"
                  placeholder="user"
                  className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  Password
                </label>
                <input
                  name="password"
                  type="password"
                  placeholder="password"
                  className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                  required
                />
              </div>
              {error ? (
                <p className="text-sm font-semibold text-[var(--secondary-purple)]">
                  {error}
                </p>
              ) : null}
              <button
                type="submit"
                className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.25em] text-white transition hover:brightness-110"
              >
                Sign in
              </button>
              <p className="text-xs text-[var(--gray-text)]">
                Demo credentials: user / password
              </p>
            </form>
          </section>
        </main>
      </div>
    );
  }

  if (isLoading || !board) {
    return (
      <div className="relative min-h-screen overflow-hidden">
        <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
        <main className="relative mx-auto flex min-h-screen max-w-xl items-center px-6 py-16">
          <section className="w-full rounded-[32px] border border-[var(--stroke)] bg-white/90 p-8 text-center shadow-[var(--shadow)] backdrop-blur">
            <h1 className="font-display text-2xl font-semibold text-[var(--navy-dark)]">
              Loading your board
            </h1>
            <p className="mt-3 text-sm text-[var(--gray-text)]">
              Fetching the latest updates from the server.
            </p>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div>
      {boardError ? (
        <div className="mx-auto max-w-[1500px] px-6 pt-6">
          <div className="rounded-2xl border border-[var(--stroke)] bg-white/90 px-4 py-3 text-sm text-[var(--secondary-purple)] shadow-[var(--shadow)]">
            {boardError}
          </div>
        </div>
      ) : null}
      <KanbanBoard
        board={board}
        onBoardChange={handleBoardChange}
        onLogout={handleLogout}
        onRenameColumn={handleRenameColumn}
        onAddCard={handleAddCard}
        onDeleteCard={handleDeleteCard}
        onMoveCard={handleMoveCard}
      />
    </div>
  );
}
