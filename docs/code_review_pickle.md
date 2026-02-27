# Code Review: Pickle Review

**Date:** 2026-02-27  
**Scope:** Full project review - backend, frontend, tests, Docker  
**Codebase:** ~1,700 lines across 13 source files

---

## Executive Summary

This is a well-structured MVP with clear separation of concerns. The previous code review identified several critical security issues, and most have been properly addressed. The codebase is clean, tests pass, and the architecture is sound.

---

## What's Been Fixed Since Last Review

The following critical issues from the previous review have been resolved:

1. **Credentials moved to env vars** - `auth.py` now reads `PM_USERNAME`/`PM_PASSWORD` from environment
2. **Session tokens are random** - Uses `secrets.token_hex(32)` with server-side session store
3. **Debug endpoint removed** - No `/api/ai/test` endpoint exists
4. **created_at preserved** - `replace_board` now fetches and preserves existing timestamps

---

## Current Issues

### High Priority

#### H1. Frontend lint errors

**File:** `frontend/src/components/AIChatSidebar.tsx:63`

```tsx
No messages yet. Start with something like "Move card-1 to Done.".
```

The double quotes are unescaped and trigger ESLint errors:
- `react/no-unescaped-entities`

**Fix:** Use `&quot;` or `'...'` instead.

---

### Medium Priority

#### M1. Missing input validation for column titles

**File:** `backend/app/models.py:17-20`

```python
class ColumnPayload(BaseModel):
    id: str
    title: str  # No max_length
    cardIds: list[str]
```

Card titles have `max_length=200` but column titles are unbounded. The AI could generate extremely long column titles.

**Fix:** Add `title: str = Field(max_length=100)` (or similar).

---

#### M2. Rate limiter is per-process, not per-worker

**File:** `backend/app/routes/ai.py:27-38`

```python
_ai_request_times: dict[str, list[float]] = {}
```

The in-memory rate limiter uses a module-level dict. When running with multiple uvicorn workers, each worker has its own counter, allowing 20 requests per worker (60+ total). For a single-container MVP this is acceptable, but worth documenting.

---

#### M3. No connection pooling / pooling configuration

**File:** `backend/app/db.py:104-108`

```python
def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
```

Each request opens a new SQLite connection. For an MVP this is fine, but for production with concurrent requests, this could cause lock contention. Consider using a connection pool or at minimum ensuring connections are properly closed (currently handled via context manager).

---

#### M4. Hardcoded board ID

**Files:** `backend/app/db.py:31`, `backend/app/routes/board.py:21,30`

```python
DEFAULT_BOARD_ID = "board-1"
```

The MVP supports only one board per user, but the board ID is hardcoded. This is documented as intentional for MVP but could cause issues if expanded.

---

### Low Priority

#### L1. Seed data duplication

**Files:** `backend/app/db.py:36-101`, `frontend/src/lib/kanban.ts:20-74`

The default columns and cards exist in both backend and frontend. There's a comment noting they must be kept in sync, but they're technically not auto-synced.

---

#### L2. No E2E tests despite Playwright setup

**File:** `frontend/playwright.config.ts`

Configured but no test files exist in `frontend/tests/`. The previous review noted this.

---

#### L3. Missing backend tests for edge cases

The backend tests cover happy paths well but lack:
- Test for `PUT /api/board` with malformed JSON (should return 422)
- Test for board replace when database is corrupted

---

#### L4. Frontend uses JSON round-trip for cloning

**File:** `frontend/src/components/KanbanBoard.tsx:22-23`

```typescript
const cloneBoard = (board: BoardData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;
```

Works fine for current scale. Not a real problem.

---

## Positive Observations

The code does many things well:

- **Pydantic validation** with discriminated unions for AI operations is clean and extensible
- **SQLite foreign keys** properly enabled with `PRAGMA foreign_keys = ON`
- **httponly cookie** prevents XSS from stealing sessions
- **samesite="lax"** is appropriate for single-origin app
- **Test coverage** is solid for core functionality
- **AI rate limiting** in-memory implementation is reasonable for MVP
- **Summary shortcut** avoids unnecessary OpenRouter calls
- **Offline fallback** with localStorage is a thoughtful UX touch
- **TypeScript strictness** prevents many runtime errors

---

## Test Results

| Suite | Status |
|-------|--------|
| Backend tests | 19 passed |
| Frontend tests | 9 passed |
| Backend ruff | Clean |
| Frontend ESLint | 2 errors |

---

## Recommendations

### Immediate (before deployment)

1. Fix the 2 ESLint errors in `AIChatSidebar.tsx`
2. Add `max_length` to `ColumnPayload.title`

### Post-MVP

1. Add Playwright E2E smoke tests
2. Consider connection pooling if scaling
3. Document single-worker limitation for rate limiting

---

## Security Posture

For an MVP running locally (as specified), the current security is adequate:
- Credentials via environment variables
- Signed session tokens with server-side validation
- httponly cookies
- No SQL injection (parameterized queries)
- Input validation via Pydantic

**Note:** The `.env` file contains `OPENROUTER_API_KEY` - ensure this is never committed.

---

## Conclusion

The codebase is production-ready for an MVP. The critical issues from the previous review have been addressed, and the remaining issues are minor or documented as intentional trade-offs for the MVP scope.
