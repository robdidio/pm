# Project Plan

This plan breaks the work into phases with checklists, tests, and success criteria. Each phase ends with a user approval checkpoint.

## Part 1: Plan and codebase discovery

Goal: Document the current frontend demo, expand this plan with production-focused steps, and confirm scope.

Checklist:
- [ ] Review existing frontend and summarize structure, components, and test setup.
- [ ] Create frontend/AGENTS.md describing the current demo implementation.
- [ ] Expand this plan into detailed checklists, tests, and success criteria for all phases.
- [ ] Confirm production-appropriate tooling choices in this plan.
- [ ] User review and approval.

Tests:
- None (documentation-only).

Success criteria:
- [ ] This plan includes checklists, tests, and success criteria for every phase.
- [ ] frontend/AGENTS.md documents the current demo accurately.
- [ ] User explicitly approves the plan before any code work.

## Part 2: Scaffolding (production-style container)

Goal: Establish a single-container production layout with FastAPI serving static assets and API routes.

Checklist:
- [ ] Define a single-container Docker layout with multi-stage build for frontend static assets.
- [ ] Add backend skeleton in backend/ using FastAPI and uv.
- [ ] Serve a minimal static page from FastAPI at / to prove static hosting.
- [ ] Add a sample API route (e.g., /api/health).
- [ ] Add start/stop scripts for Windows, macOS, and Linux in scripts/.
- [ ] Document container build/run steps in docs/ (concise).
- [ ] User review and approval.

Tests:
- [ ] Backend unit test for /api/health (pytest + httpx).
- [ ] Minimal smoke test to confirm static / loads (Playwright or HTTP test).

Success criteria:
- [ ] Single container builds and runs locally.
- [ ] / serves static HTML and /api/health returns expected JSON.
- [ ] Scripts work on each OS.

## Part 3: Integrate frontend build

Goal: Build and serve the existing NextJS demo as static output from FastAPI.

Checklist:
- [ ] Configure NextJS to build static output suitable for serving from FastAPI.
- [ ] Copy built assets into backend static directory during Docker build.
- [ ] Serve the demo Kanban board at /.
- [ ] Update documentation with run/build notes.
- [ ] User review and approval.

Tests:
- [ ] Frontend unit tests (Vitest).
- [ ] E2E test that / renders the board (Playwright).

Success criteria:
- [ ] The demo board loads at / from the container.
- [ ] Unit and E2E tests pass.

## Part 4: Fake sign-in flow

Goal: Gate the board behind a simple login for "user" / "password" and allow logout.

Checklist:
- [ ] Add login UI and session handling (cookie or local storage) in frontend.
- [ ] Add backend auth check for protected API endpoints.
- [ ] Add logout flow that clears session.
- [ ] User review and approval.

Tests:
- [ ] Frontend unit tests for login/logout states.
- [ ] E2E test: cannot access board before login; can after login; can logout.

Success criteria:
- [ ] Only authenticated users see the board.
- [ ] Login/logout flows are stable and tested.

## Part 5: Database modeling

Goal: Define schema for a single-board Kanban per user and document storage strategy.

Checklist:
- [ ] Propose a relational schema JSON (tables, fields, relationships).
- [ ] Propose a document schema JSON (aggregate document shape).
- [ ] Save both JSON schemas under docs/.
- [ ] Document database approach in docs/ (migrations, initialization, constraints).
- [ ] User review and approval.

Tests:
- None (documentation-only).

Success criteria:
- [ ] Two JSON schema documents exist (relational and document).
- [ ] Database approach is documented and approved.

## Part 6: Backend Kanban APIs

Goal: Implement CRUD endpoints for the Kanban board with SQLite persistence.

Checklist:
- [ ] Add database initialization and schema creation on startup if missing.
- [ ] Implement endpoints to read/update columns and cards.
- [ ] Enforce user scoping (single user for MVP, structure supports multi-user).
- [ ] Add API validation models and error handling.
- [ ] User review and approval.

Tests:
- [ ] Backend unit tests for each endpoint (pytest + httpx).
- [ ] Database integration tests for persistence.

Success criteria:
- [ ] CRUD endpoints work and persist to SQLite.
- [ ] Tests cover success and failure cases.

## Part 7: Frontend + backend integration

Goal: Replace local demo state with API-driven persistence.

Checklist:
- [ ] Connect frontend to backend API for board data.
- [ ] Update drag/drop and edits to persist via API.
- [ ] Add loading, error, and retry states.
- [ ] User review and approval.

Tests:
- [ ] Frontend unit tests for API interactions.
- [ ] E2E tests covering add/move/edit/delete via API.

Success criteria:
- [ ] Board changes persist across refreshes.
- [ ] UI handles API errors gracefully.

## Part 8: AI connectivity

Goal: Establish OpenRouter connectivity from the backend.

Checklist:
- [ ] Add OpenRouter client using env key.
- [ ] Implement a test endpoint calling model with a simple prompt.
- [ ] User review and approval.

Tests:
- [ ] Backend integration test that validates connectivity (skipped when no key).

Success criteria:
- [ ] "2+2" test returns expected content.
- [ ] Failures are handled with clear errors.

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