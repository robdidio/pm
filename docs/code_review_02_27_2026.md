# Code Review — 2026-02-27

Reviewer: Claude Code (claude-sonnet-4-6)
Scope: Full codebase — backend, frontend, tests, Docker, config

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High     | 4 |
| Medium   | 7 |
| Low      | 9 |

---

## Critical

### C1 — API key committed to `.env`

**File:** `.env`

The `OPENROUTER_API_KEY` is present in plaintext and has been committed to git history. Any party with repo access can extract it.

**Fix:**
- Revoke the key immediately via the OpenRouter dashboard.
- Remove `.env` from git history (`git filter-repo --path .env --invert-paths`).
- Ensure `.env` is in `.gitignore` (verify it is not tracked).
- Document in README that developers must create `.env` locally.

---

## High

### H1 — Race condition in in-memory session store

**File:** `backend/app/main.py` — `create_session` / session eviction logic

The `_active_sessions` dictionary is mutated (eviction loop + insert) without a lock. FastAPI runs in a thread pool; concurrent login requests can corrupt the dict.

**Fix:** Wrap mutations in a `threading.Lock()` (or `asyncio.Lock()` if the handlers are async). Same concern applies to `_login_attempts` (rate limiter) and `_ai_request_times`.

---

### H2 — Timing attack on credential comparison

**File:** `backend/app/main.py` — login route

```python
if payload.username != valid_username or payload.password != valid_password:
```

Short-circuit string comparison leaks information about which field is wrong and how many characters match via response-time differences.

**Fix:** Use `secrets.compare_digest()` for both comparisons, and always compare both fields regardless of the first result:

```python
ok_user = secrets.compare_digest(payload.username, valid_username)
ok_pass = secrets.compare_digest(payload.password, valid_password)
if not (ok_user and ok_pass):
    ...
```

---

### H3 — AI JSON fallback parser can accept truncated/partial responses

**File:** `backend/app/main.py` — AI response parsing

When the AI returns invalid JSON the fallback logic finds the first `{` and last `}` in the raw string and tries to parse that substring. This can silently accept a truncated response that happens to be balanced (e.g., a partial board state), leading to data corruption.

**Fix:** Do not attempt to salvage malformed JSON. Reject the response entirely and return `502 openrouter_invalid_json`. Enforce structured output from the model at the prompt / API-parameter level instead.

---

### H4 — CSP allows `unsafe-inline` for scripts

**File:** `backend/app/main.py` — CSP header definition

`script-src 'self' 'unsafe-inline'` substantially weakens XSS protection. Any injected script content would execute.

**Fix:** Next.js static exports require inline scripts for hydration. Document the constraint explicitly. For a hardened build, investigate Next.js nonce-based CSP support so `unsafe-inline` can be dropped in favour of per-request nonces.

---

## Medium

### M1 — No CSRF mitigation beyond SameSite cookie

**File:** `backend/app/main.py` — state-changing routes (`PUT /api/board`, `POST /api/ai/board`, `POST /api/auth/logout`)

`SameSite=Strict` on the session cookie provides good default protection, but only as long as the app is not embedded in an iframe or served on a subdomain. There is no additional CSRF token check.

**Fix:** For an MVP served on a single origin this is acceptable. Add a `Sec-Fetch-Site` / `Origin` header check if subdomain scenarios arise, or implement a double-submit CSRF token.

---

### M2 — In-memory rate limiting does not survive restarts or scale out

**File:** `backend/app/main.py` — `_login_attempts`, `_ai_request_times`

Rate-limit state is lost on every container restart. A single bad actor gets a fresh budget after each restart. In a multi-replica deployment, each replica has independent state.

**Fix:** For this MVP (single container) the risk is low. Document the limitation. For production, move rate-limit state to Redis or a sidecar.

---

### M3 — Card `id` field not validated against its dict key in AI response

**File:** `backend/app/main.py` — AI response schema validation

The validator checks that each card has an `id` field but does not assert `card["id"] == key`. An AI response with mismatched keys would pass validation and produce an inconsistent board.

**Fix:**

```python
if card_data.get("id") != card_id:
    raise HTTPException(status_code=502, detail="openrouter_invalid_schema")
```

---

### M4 — User message added to chat before request completes

**File:** `frontend/src/components/KanbanBoard.tsx` — AI submit handler

The user's message is appended to `chatMessages` before the API call is made. If the request fails, the user sees their message but no response, with no retry affordance and no clear error beyond a banner.

**Fix:** Either (a) optimistically add the message but show a "failed — retry" action on error, or (b) wait for a successful response before committing the message to state.

---

### M5 — No React error boundary

**File:** `frontend/src/components/KanbanBoard.tsx` (and subtree)

An unhandled render error anywhere in the board component tree produces a blank screen with no recovery path.

**Fix:** Wrap the board (and optionally the AI sidebar) in an `ErrorBoundary` component that renders a fallback UI and a reload prompt.

---

### M6 — `replace_board` relies on implicit SQLite transaction

**File:** `backend/app/db.py` — `replace_board`

The delete-then-insert sequence runs without an explicit `BEGIN` / `COMMIT`. If the process is killed between the delete and the insert, the board is lost.

**Fix:**

```python
with conn:  # context manager commits on success, rolls back on exception
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))
    conn.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))
    # ... inserts ...
```

Verify the existing `with` usage already does this; if not, make it explicit.

---

### M7 — Seed data duplicated between backend and frontend

**File:** `backend/app/db.py` — seed data; `frontend/src/lib/kanban.ts` — `initialData`

The two copies can silently diverge. There is no test asserting they match.

**Fix:** Add a backend test that compares `seed_board` output with the frontend's `initialData` JSON (checked-in as a shared fixture), or generate the frontend constant from the backend at build time.

---

## Low

### L1 — `createId` uses `Math.random()` (non-cryptographic)

**File:** `frontend/src/lib/kanban.ts` — `createId`

For a single-user local app the collision probability is negligible. However, if IDs are ever used in a multi-user or server-side context, `Math.random()` is not safe.

**Note:** Acceptable for MVP. Generate IDs server-side for a multi-user build.

---

### L2 — No global exception handler — stack traces may leak

**File:** `backend/app/main.py`

Unhandled exceptions return FastAPI's default 500 response which can include a traceback in development mode.

**Fix:** Add an `@app.exception_handler(Exception)` that logs the full error and returns a sanitised `{"detail": "internal_error"}`.

---

### L3 — No audit logging for board mutations

**File:** `backend/app/main.py` — `PUT /api/board`, `POST /api/ai/board`

Only a summary log line is emitted on save. There is no record of what changed, when, or triggered by which path (user drag-and-drop vs AI operation).

**Fix:** Log operation type, column/card counts before and after, and source (`user` vs `ai`) at `INFO` level.

---

### L4 — `Content-Type: application/json` not explicitly enforced

**File:** `backend/app/main.py` — board and AI routes

FastAPI's Pydantic validation will reject malformed bodies, but a non-JSON `Content-Type` is not explicitly rejected. This can produce confusing 422 errors.

**Fix:** Add a middleware or dependency that returns `415 Unsupported Media Type` when `Content-Type` is missing or not `application/json` on POST/PUT routes.

---

### L5 — AI operation models lack docstrings

**File:** `backend/app/main.py` — `AiOperation*` Pydantic models

The operation union types (`add_card`, `move_card`, `update_card`, `delete_card`, `add_column`, `delete_column`) have no docstrings explaining semantics or field constraints.

**Fix:** Add one-line docstrings. This also helps if the models are ever serialised to an OpenAPI schema used to drive the AI prompt.

---

### L6 — Docker image runs as root

**File:** `Dockerfile`

The container does not create or switch to a non-root user. A process escape would have full container privileges.

**Fix:**

```dockerfile
RUN useradd -m appuser
USER appuser
```

Ensure the data directory (`/app/data`) is writable by the new user.

---

### L7 — No `.dockerignore`

**File:** repo root

Without a `.dockerignore`, `docker build` copies the entire working tree (including `node_modules`, `.git`, `.env`) into the build context, slowing builds and potentially baking secrets into the image.

**Fix:** Add a `.dockerignore` excluding at minimum: `.git`, `.env`, `node_modules`, `frontend/.next`, `backend/__pycache__`, `*.pyc`.

---

### L8 — `SESSION_TTL` and `MAX_SESSIONS` are magic numbers

**File:** `backend/app/main.py`

Session configuration values are defined as module-level constants with no surrounding documentation explaining why those values were chosen.

**Fix:** Add brief inline comments, e.g.:

```python
SESSION_TTL = 8 * 3600   # 8 hours — matches a typical work day
MAX_SESSIONS = 50        # single-user MVP; cap prevents unbounded memory growth
```

---

### L9 — Frontend has no loading skeleton for initial board fetch

**File:** `frontend/src/app/page.tsx`, `frontend/src/components/KanbanBoard.tsx`

While the board is loading from the API the page renders nothing (or a blank column area). On slow connections this looks broken.

**Fix:** Render a lightweight skeleton (grey column placeholders) while `boardData` is `null`.

---

## Good Practices Observed

- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP) applied via middleware.
- Session cookie is `HttpOnly`, `SameSite=Strict`, and `Secure` in production.
- Pydantic models enforce length limits on all user-supplied text fields.
- AI response schema is validated before the board is mutated.
- Test suite covers happy-path board CRUD, auth, and AI operation application.
- `tmp_path`-based DB isolation in tests — no shared state between test cases.
- `localStorage` fallback prevents total data loss when the API is unreachable.
- Clean separation of concerns: DB helpers, route handlers, and models are well-organised.
