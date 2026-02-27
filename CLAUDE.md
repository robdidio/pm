# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A single-board Kanban project management app. NextJS frontend + Python FastAPI backend, packaged in a Docker container. The backend serves the static NextJS export at `/` and exposes API endpoints under `/api/`.

Credentials: `user` / `password` (hardcoded for MVP).

## Commands

### Run the app (Docker)

```bash
# Windows
scripts/start.ps1

# macOS/Linux
scripts/start.sh

# Manual
docker build -t pm-app .
docker run -d --name pm-app -p 8000:8000 --env-file .env pm-app
```

App runs at http://localhost:8000/

### Backend tests

```bash
cd backend
PYTHONPATH=. uv run --with pytest --with httpx --with fastapi --with uvicorn --with pydantic pytest --tb=short -q
PYTHONPATH=. uv run --with pytest --with httpx --with fastapi --with uvicorn --with pydantic pytest tests/test_board.py
PYTHONPATH=. uv run --with pytest --with httpx --with fastapi --with uvicorn --with pydantic pytest tests/test_board.py::test_get_board_returns_seed
```

The OpenRouter connectivity test (`test_ai.py::test_openrouter_connectivity`) is skipped when `OPENROUTER_API_KEY` is not set — this is expected.

### Frontend tests

```bash
cd frontend
npm test                        # unit tests (vitest)
npm run test:unit:watch         # watch mode
npm run test:e2e                # playwright e2e
npm run test:all                # both
```

### Frontend dev server

```bash
cd frontend
npm run dev     # Next.js dev server (frontend only, no API)
npm run build   # static export (output in out/)
npm run lint
```

## Architecture

### Data flow

The board state is the single source of truth: `BoardData = { columns: Column[], cards: Record<string, Card> }`. The frontend always sends the full board on save (`PUT /api/board`); the backend does a full replace (delete + insert) on every write.

### Backend (`backend/`)

- `app/main.py` — all FastAPI routes, Pydantic models, AI integration, auth logic
- `app/db.py` — SQLite helpers: `init_db`, `fetch_board`, `replace_board`, `seed_board`
- Auth: cookie-based (`pm_session`). `require_auth()` guard on all board/AI routes.
- DB path: `/app/data/pm.db` in container; overridable via `PM_DB_PATH` env var or `app.state.db_path` (used in tests with `tmp_path`).
- AI endpoint (`POST /api/ai/board`): sends full conversation history + board context as system prompt to OpenRouter (`openai/gpt-oss-120b`). Response is a versioned JSON object with `{ schemaVersion, board, operations, assistantMessage }`. Summary requests are short-circuited locally without an API call.

### Frontend (`frontend/src/`)

- `app/page.tsx` — root page: renders `<LoginPanel>` or `<KanbanBoard>` based on auth check
- `components/KanbanBoard.tsx` — main board component; owns all state, API calls, and AI chat logic
- `components/AIChatSidebar.tsx` — chat UI (stateless, controlled by KanbanBoard)
- `components/KanbanColumn.tsx` + `KanbanCard.tsx` + `KanbanCardPreview.tsx` + `NewCardForm.tsx` — board UI
- `lib/kanban.ts` — pure data utilities: `moveCard`, `createId`, `initialData`
- Drag-and-drop via `@dnd-kit`. Fallback: if API is unreachable, board state persists to `localStorage` (`pm_local_board`).

### Docker build

Two-stage: Node 20 builds the Next.js static export, then Python 3.12-slim serves it. Frontend `out/` is copied to `backend/app/static/`. Dependencies managed with `uv`.

## Key conventions

- No emojis anywhere in code or output.
- Simplicity over abstraction — no over-engineering.
- Identify root cause before fixing; don't guess.
- Color scheme: accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, gray `#888888`.
- AI model: `openai/gpt-oss-120b` via OpenRouter. API key in `.env` as `OPENROUTER_API_KEY`.
