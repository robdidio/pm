# Project Plan

This plan breaks the work into phases with checklists, tests, and success criteria. Each phase ends with a user approval checkpoint.

## Part 1: Plan and codebase discovery

Goal: Document the current frontend demo, expand this plan with production-focused steps, and confirm scope.

Checklist:
- [x] Review existing frontend and summarize structure, components, and test setup.
- [x] Create frontend/AGENTS.md describing the current demo implementation.
- [x] Expand this plan into detailed checklists, tests, and success criteria for all phases.
- [x] Confirm production-appropriate tooling choices in this plan.
- [x] User review and approval.

Tests:
- None (documentation-only).

Success criteria:
- [x] This plan includes checklists, tests, and success criteria for every phase.
- [x] frontend/AGENTS.md documents the current demo accurately.
- [x] User explicitly approves the plan before any code work.

## Part 2: Scaffolding (production-style container)

Goal: Establish a single-container production layout with FastAPI serving static assets and API routes.

Checklist:
- [x] Define a single-container Docker layout with multi-stage build for frontend static assets.
- [x] Add backend skeleton in backend/ using FastAPI and uv.
- [x] Serve a minimal static page from FastAPI at / to prove static hosting.
- [x] Add a sample API route (e.g., /api/health).
- [x] Add start/stop scripts for Windows, macOS, and Linux in scripts/.
- [x] Document container build/run steps in docs/ (concise).
- [x] User review and approval.

Decisions:
- Single-container Docker build with a Node build stage and FastAPI serving static output.

Tests:
- [x] Backend unit test for /api/health (pytest + httpx).
- [x] Minimal smoke test to confirm static / loads (Playwright or HTTP test).

Success criteria:
- [x] Single container builds and runs locally.
- [x] / serves static HTML and /api/health returns expected JSON.
- [x] Scripts work on each OS (macOS/Linux unverified by agent; user approved).

## Part 3: Integrate frontend build

Goal: Build and serve the existing NextJS demo as static output from FastAPI.

Checklist:
- [x] Configure NextJS to build static output suitable for serving from FastAPI.
- [x] Copy built assets into backend static directory during Docker build.
- [x] Serve the demo Kanban board at /.
- [x] Update documentation with run/build notes.
- [x] User review and approval.

Decisions:
- NextJS uses static export with trailing slashes and unoptimized images.
- FastAPI serves static assets at /.

Tests:
- [x] Frontend unit tests (Vitest).
- [x] E2E test that / renders the board (Playwright).

Success criteria:
- [x] The demo board loads at / from the container.
- [x] Unit and E2E tests pass.

## Part 4: Fake sign-in flow

Goal: Gate the board behind a simple login for "user" / "password" and allow logout.

Checklist:
- [x] Add login UI and session handling (cookie or local storage) in frontend.
- [x] Add backend auth check for protected API endpoints.
- [x] Add logout flow that clears session.
- [x] User review and approval.

Decisions:
- Backend auth uses a simple HTTP-only cookie named pm_session.
- Frontend uses a localStorage fallback for dev when auth endpoints are unavailable.

Tests:
- [x] Frontend unit tests for login/logout states.
- [x] E2E test: cannot access board before login; can after login; can logout.

Success criteria:
- [x] Only authenticated users see the board.
- [x] Login/logout flows are stable and tested.

## Part 5: Database modeling

Goal: Define schema for a single-board Kanban per user and document storage strategy.

Checklist:
- [x] Propose a relational schema JSON (tables, fields, relationships).
- [x] Propose a document schema JSON (aggregate document shape).
- [x] Save both JSON schemas under docs/.
- [x] Document database approach in docs/ (migrations, initialization, constraints).
- [x] User review and approval.

Tests:
- None (documentation-only).

Success criteria:
- [x] Two JSON schema documents exist (relational and document).
- [x] Database approach is documented and approved.

## Part 6: Backend Kanban APIs

Goal: Implement CRUD endpoints for the Kanban board with SQLite persistence.

Checklist:
- [x] Add database initialization and schema creation on startup if missing.
- [x] Implement endpoints to read/update columns and cards.
- [x] Enforce user scoping (single user for MVP, structure supports multi-user).
- [x] Add API validation models and error handling.
- [x] User review and approval.

Decisions:
- Full-board replace model for updates (single PUT with columns/cards).
- Database stored at /app/data/pm.db in the container.

Tests:
- [x] Backend unit tests for each endpoint (pytest + httpx).
- [x] Database integration tests for persistence.

Success criteria:
- [x] CRUD endpoints work and persist to SQLite.
- [x] Tests cover success and failure cases.

## Part 7: Frontend + backend integration

Goal: Replace local demo state with API-driven persistence.

Checklist:
- [x] Connect frontend to backend API for board data.
- [x] Update drag/drop and edits to persist via API.
- [x] Add loading, error, and retry states.
- [x] User review and approval.

Decisions:
- Frontend falls back to localStorage when API routes are missing/unreachable.
- Save operations show a lightweight "Saving changes" state.

Tests:
- [x] Frontend unit tests for API interactions.
- [x] E2E tests covering add/move/edit/delete via API.

Success criteria:
- [x] Board changes persist across refreshes.
- [x] UI handles API errors gracefully.

## Part 8: AI connectivity

Goal: Establish OpenRouter connectivity from the backend.

Checklist:
- [x] Add OpenRouter client using env key.
- [x] Implement a test endpoint calling model with a simple prompt.
- [x] User review and approval.

Decisions:
- Backend uses OpenRouter chat completions with model openai/gpt-oss-120b.
- /api/ai/test is protected by auth and returns the raw model response.

Tests:
- [x] Backend integration test that validates connectivity (skipped when no key).

Success criteria:
- [x] "2+2" test returns expected content.
- [x] Failures are handled with clear errors.

## Part 9: AI structured outputs for Kanban updates

Goal: Provide board context to the AI and accept structured updates.

Checklist:
- [ ] Define structured output schema for AI responses.
- [ ] Include board JSON + conversation history in prompts.
- [ ] Validate and apply AI-suggested board updates.
- [ ] User review and approval.

Tests:
- [ ] Backend tests for schema validation and safe update application.
- [ ] Mocked AI responses in unit tests.

Success criteria:
- [ ] AI responses are validated and deterministic to apply.
- [ ] Invalid AI responses do not break the board.

## Part 10: AI chat sidebar UX

Goal: Add AI chat UI that can update the board from structured outputs.

Checklist:
- [ ] Build sidebar chat UI with message history.
- [ ] Wire chat to backend AI endpoint.
- [ ] Apply structured output updates to the board and refresh UI.
- [ ] User review and approval.

Tests:
- [ ] Frontend unit tests for chat state and rendering.
- [ ] E2E tests for chat prompt and board update flow.

Success criteria:
- [ ] Chat works end to end with board updates.
- [ ] UI remains responsive and consistent after AI changes.