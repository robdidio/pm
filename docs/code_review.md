# Code Review Report

**Date:** 2026-02-27
**Scope:** Full repository review — backend, frontend, tests, Docker
**Codebase size:** ~1,600 lines of production code across 13 source files

---

## Summary

The app is a well-structured MVP. The separation of concerns is clear, TypeScript types are strict, Pydantic models provide good schema validation, and the graceful offline fallback is a thoughtful touch. That said, there are several issues — some security-critical — that should be resolved before the app is deployed to any shared or production environment.

Issues are grouped by severity: **Critical**, **Medium**, and **Low**.

---

## Critical Issues

### C1. Credentials hardcoded in source code

**Files:** `backend/app/main.py:33-34`, `frontend/src/app/page.tsx:10-11`

The backend defines the only valid login credentials as constants:

```python
VALID_USERNAME = "user"
VALID_PASSWORD = "password"
```

The frontend duplicates them to support its offline fallback:

```typescript
const DEMO_USERNAME = "user";
const DEMO_PASSWORD = "password";
```

These are committed to version control. Any developer with repository access has the credentials. They should be moved to environment variables, read at startup, and the frontend constants deleted entirely (the offline login bypass should use a different mechanism or be removed).

**Action:** Load credentials from env vars in the backend. Remove `DEMO_USERNAME`/`DEMO_PASSWORD` from the frontend.

---

### C2. Session cookie is a static, predictable string

**File:** `backend/app/main.py:31-32, 119-120, 347-354`

Authentication is implemented by comparing the cookie value to a fixed string:

```python
AUTH_COOKIE_VALUE = "authenticated"

def is_authenticated(request: Request) -> bool:
    return request.cookies.get(AUTH_COOKIE_NAME) == AUTH_COOKIE_VALUE
```

Any client that sends `pm_session=authenticated` is treated as logged in. There is no session token, no server-side session store, and no signature. The cookie is also set with `secure=False`, so it can be intercepted over HTTP.

**Action:** Generate a cryptographically random session token per login and store it server-side (or use a signed cookie via `itsdangerous`). Set `secure=True` in production. Add an expiry.

---

### C3. Client-side auth bypass exposes credentials in JavaScript

**File:** `frontend/src/app/page.tsx:33-39, 64-69`

When the API is unreachable the frontend checks `localStorage.getItem("pm_local_auth") === "true"`. This flag is set after a successful login, but the code also checks the hardcoded credentials on a 404 from the login endpoint:

```typescript
if (response.status === 404) {
  if (username === DEMO_USERNAME && password === DEMO_PASSWORD) {
    localStorage.setItem(LOCAL_AUTH_KEY, "true");
    setAuthState("authenticated");
  }
}
```

Any user can inspect the minified bundle and find the hardcoded credentials. Worse, anyone can set `localStorage.pm_local_auth = "true"` in the browser console to bypass the login screen entirely (the board will then load from `initialData` or the local cache, not the real server, but the UI shows them as authenticated).

**Action:** Remove the offline credential check. The offline fallback can allow local access without credentials, or it can be removed if offline support is not a requirement.

---

### C4. Debug/test endpoint left in production

**File:** `backend/app/main.py:426-430`

```python
@app.post("/api/ai/test")
def ai_test(request: Request) -> dict[str, str]:
    require_auth(request)
    response = call_openrouter("What is 2+2? Respond with a single number.")
    return {"response": response}
```

This endpoint makes a live API call to OpenRouter. Any authenticated user can invoke it repeatedly to incur API costs. It has no rate limiting and serves no production purpose.

**Action:** Delete this endpoint and its associated test in `test_ai.py`.

---

### C5. `replace_board` silently destroys card creation timestamps

**File:** `backend/app/db.py:248-285`

`replace_board` deletes all cards and re-inserts them:

```python
conn.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))
```

Then inserts each card with `created_at = now`:

```python
now = utc_now()
for card in cards:
    conn.execute(
        "INSERT INTO cards (..., created_at, updated_at) VALUES (..., ?, ?)",
        (..., now, now),
    )
```

Every save operation resets `created_at` on every card to the current time. The schema includes `created_at` as a meaningful timestamp, but it is overwritten on every board save. This is a data integrity bug; all historical creation times are lost.

**Action:** Either remove `created_at`/`updated_at` from the schema if they are not needed, or use `INSERT OR REPLACE` with `ON CONFLICT` to preserve `created_at` and only update `updated_at` when the card content changes.

---

## Medium Issues

### M1. Error messages leak internal data

**File:** `backend/app/main.py:197-214`

Validation errors expose card IDs from the internal data model:

```python
raise HTTPException(
    status_code=400,
    detail=f"missing_card:{card_id}",
)
# ...
raise HTTPException(status_code=400, detail=f"unused_cards:{extra_cards}")
```

These messages appear in API responses. While the data is low-sensitivity for an MVP, the pattern is a bad habit that should not be carried forward.

**Action:** Return generic error codes (`"invalid_board"`) and log the details server-side.

---

### M2. No input length limits on card content

**Files:** `backend/app/main.py:42-46`, `frontend/src/components/NewCardForm.tsx`

`CardPayload` accepts `title` and `details` as unbounded strings:

```python
class CardPayload(BaseModel):
    id: str
    title: str
    details: str
```

A user (or the AI) could write a card title thousands of characters long. The system prompt sent to OpenRouter includes the full board as JSON, so unbounded content directly increases API token usage and cost.

**Action:** Add `max_length` constraints in the Pydantic model and matching `maxLength` attributes on frontend inputs.

---

### M3. No rate limiting on the AI endpoint

**File:** `backend/app/main.py:381`

The `/api/ai/board` endpoint makes a call to OpenRouter on every request. There is no rate limiting, no per-session request count, and no cost cap. A user can send continuous requests in a loop.

**Action:** Add a simple in-memory rate limiter (e.g., using a token bucket per session) or a per-minute request cap. For a production deployment, use a middleware such as `slowapi`.

---

### M4. Full board delete-and-replace on every save

**File:** `backend/app/db.py:248-285`

Every card move, rename, or addition deletes all rows and re-inserts the entire board. This is correct for correctness but is inefficient and prevents meaningful use of `updated_at` on individual cards. It also means that if a card insert fails mid-write, the board is left in a partially written state (columns deleted, cards not yet inserted).

The operation does run inside a SQLite connection context manager, which commits on exit and rolls back on exception, so the atomicity concern is mitigated — but it is worth verifying that `get_connection` opens a transaction that covers both the DELETE and INSERT statements.

**Action:** Verify that the `with get_connection(...) as conn` block is transactional. For future scale, consider a differential update approach, but this is low priority for a single-user MVP.

---

### M5. Seed data duplicated between backend and frontend

**Files:** `backend/app/db.py:35-100`, `frontend/src/lib/kanban.ts:18-72`

The eight default cards and five default columns are defined identically in two places. The frontend copy is used when the API is unreachable; the backend copy is used to seed the database. If one is updated the other can drift silently.

**Action:** Accept the duplication as a known trade-off for the offline fallback, and add a comment in both files noting that they must be kept in sync, or remove the frontend offline fallback entirely.

---

### M6. No CSRF protection on state-changing endpoints

**File:** `backend/app/main.py:342-361, 371-430`

The `PUT /api/board` and `POST /api/ai/board` endpoints rely solely on the session cookie for authentication. Because the cookie is `samesite="lax"`, cross-site POST requests from other origins are blocked by modern browsers in most cases. However, `lax` does not protect against same-site subdomain attacks and is not a substitute for explicit CSRF tokens.

**Action:** For now, `samesite="lax"` is acceptable for a single-origin app. If the app is ever deployed with subdomains or third-party integrations, add CSRF token validation. Document the current posture.

---

### M7. Dead code: `call_openrouter` function is never used

**File:** `backend/app/main.py:172-175`

```python
def call_openrouter(prompt: str) -> str:
    return call_openrouter_messages([
        {"role": "user", "content": prompt},
    ])
```

This function exists but is never called in production code. It was presumably extracted when the codebase moved to multi-turn conversations but the single-turn helper was not removed.

**Action:** Delete `call_openrouter`.

---

### M8. Dead code: redundant summary check after AI call

**File:** `backend/app/main.py:410-412`

```python
if not ai_response.assistantMessage and is_summary_request(payload.messages):
    summary = build_board_summary(ai_response.board)
    ai_response = ai_response.model_copy(update={"assistantMessage": summary})
```

The `is_summary_request` check at line 390 short-circuits the function and returns early before ever calling the AI. This check at line 410 is therefore unreachable for summary requests. It would only execute if a summary request somehow passed the first check, which cannot happen given the current logic.

**Action:** Delete lines 410-412.

---

## Low Issues

### L1. Logger declared but barely used

**File:** `backend/app/main.py:15`

```python
logger = logging.getLogger("pm.ai")
```

The logger is used in exactly one place (`parse_ai_board_response`). The rest of the application produces no structured log output. Request logging, auth events, and board saves are all silent.

**Action:** Add log calls at key points (login, board save, AI request). Configure the uvicorn log format in the `CMD` invocation.

---

### L2. `ColumnInput.card_ids` field is never used

**File:** `backend/app/db.py:14-19`

```python
@dataclass(frozen=True)
class ColumnInput:
    id: str
    title: str
    position: int
    card_ids: list[str]
```

`card_ids` is populated in `build_board_inputs` but is never read in `replace_board` or anywhere else. The column-to-card relationship is stored on `CardInput.column_id`, not on this field.

**Action:** Remove `card_ids` from `ColumnInput`.

---

### L3. Docker container runs as root

**File:** `Dockerfile`

The container has no `USER` instruction and no `HEALTHCHECK`. It runs uvicorn as root, which increases blast radius if a vulnerability is exploited.

**Action:**

```dockerfile
RUN useradd -r -s /bin/false appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/api/health || exit 1
```

---

### L4. `npm install` in Docker uses no lockfile

**File:** `Dockerfile:6`

```dockerfile
RUN npm install --no-audit --no-fund
```

`npm install` without `--frozen-lockfile` (or `npm ci`) will update packages if the lockfile allows newer versions. This means two builds from the same `Dockerfile` can produce different frontend bundles.

**Action:** Use `npm ci` instead of `npm install` to ensure reproducible builds.

---

### L5. `cloneBoard` uses JSON round-trip

**File:** `frontend/src/components/KanbanBoard.tsx:22-23`

```typescript
const cloneBoard = (board: BoardData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;
```

This works correctly but is the slowest way to deep-clone a plain object. The board data is simple (no `Date` objects, no class instances), so the only actual deep nesting is `columns[n].cardIds`. All board mutations in this file use spread operators correctly, so `cloneBoard` is only called in the load fallback path (`cloneBoard(fallback)`) and is not on a hot path. This is a minor style issue.

**Action:** Low priority — acceptable for current scale. If board size grows, replace with structured clone or a targeted copy.

---

### L6. Frontend maps over `column.cardIds` without guarding against missing cards

**File:** `frontend/src/components/KanbanBoard.tsx:389`

```typescript
cards={column.cardIds.map((cardId) => board.cards[cardId])}
```

If a `cardId` in `column.cardIds` has no matching entry in `board.cards`, this produces `undefined` in the array passed to `KanbanColumn`. The backend validates this consistency, but the frontend does not. The child component would receive an `undefined` card and likely crash or render nothing without a useful error.

**Action:** Filter out missing cards: `column.cardIds.flatMap((id) => board.cards[id] ? [board.cards[id]] : [])`.

---

### L7. No E2E test files despite Playwright configuration

**File:** `frontend/playwright.config.ts`

Playwright is configured but no test files exist in the frontend test directory. The `npm run test:e2e` script is documented and set up but runs zero tests.

**Action:** Add at least one smoke E2E test: load the app, log in, verify the board renders, move a card, confirm the save. This would catch regressions in the Docker build-and-serve pipeline that unit tests cannot.

---

### L8. Missing backend test cases

**File:** `backend/tests/`

Current backend tests cover the happy path and one invalid-credentials case. Missing coverage:

- `PUT /api/board` with a `cardId` that exists in `columns` but not in `cards` (the 400 `missing_card` path)
- `PUT /api/board` with a card in `cards` that is not referenced by any column (the 400 `unused_cards` path)
- `POST /api/ai/board` with no `OPENROUTER_API_KEY` set (the 500 `missing_openrouter_key` path)
- `POST /api/ai/board` with an empty `messages` list (the 400 `missing_messages` path)

**Action:** Add parametrised tests for the above cases.

---

## Positive Observations

These things are done well and should be preserved:

- **Pydantic discriminated union for AI operations** (`AiOperation` with `Literal` discriminator) is clean and extensible.
- **`is_authenticated` as a pure function** (reads only from the request) keeps auth logic testable without mocking state.
- **Offline fallback with localStorage** is a thoughtful degradation strategy for a single-page app.
- **`monkeypatch` in AI tests** avoids any network calls in the test suite; the tests are fast and deterministic.
- **Collision detection strategy in drag-and-drop** (pointer-within first, then closest-corners) is the correct approach for this layout.
- **`httponly=True` on the session cookie** prevents JavaScript access to the cookie value.
- **`samesite="lax"`** on the cookie is appropriate for a first-party single-origin app.
- **`PRAGMA foreign_keys = ON`** is set correctly in `get_connection`, ensuring referential integrity in SQLite.

---

## Action Priority List

| # | Issue | File(s) | Priority |
|---|-------|---------|----------|
| ~~C1~~ | ~~Move credentials to env vars, remove from source~~ | ~~`main.py`, `page.tsx`~~ | ~~Critical~~ — fixed |
| ~~C2~~ | ~~Replace static cookie value with signed session token~~ | ~~`main.py`~~ | ~~Critical~~ — fixed |
| ~~C3~~ | ~~Remove client-side credential check and localStorage auth bypass~~ | ~~`page.tsx`~~ | ~~Critical~~ — fixed |
| ~~C4~~ | ~~Delete `/api/ai/test` debug endpoint~~ | ~~`main.py`~~ | ~~Critical~~ — fixed |
| ~~C5~~ | ~~Fix `created_at` being overwritten on every board save~~ | ~~`db.py`~~ | ~~Critical~~ — fixed |
| M1 | Return generic error codes, log details server-side | `main.py` | Medium |
| M2 | Add max-length constraints to card title and details | `main.py`, `NewCardForm.tsx` | Medium |
| M3 | Add rate limiting to AI endpoint | `main.py` | Medium |
| M7 | Delete unused `call_openrouter` function | `main.py` | Medium |
| M8 | Delete unreachable summary-check block after AI call | `main.py` | Medium |
| L2 | Remove unused `card_ids` field from `ColumnInput` | `db.py` | Low |
| L3 | Add `USER` and `HEALTHCHECK` to Dockerfile | `Dockerfile` | Low |
| L4 | Replace `npm install` with `npm ci` in Docker build | `Dockerfile` | Low |
| L6 | Guard against missing cards when mapping `cardIds` | `KanbanBoard.tsx` | Low |
| L7 | Add at least one Playwright E2E smoke test | `frontend/tests/` | Low |
| L8 | Add missing backend test cases for error paths | `backend/tests/` | Low |
| L1 | Add structured logging at key events | `main.py` | Low |
| M5 | Document seed data duplication | `db.py`, `kanban.ts` | Low |
