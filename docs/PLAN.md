# Project plan (detailed)

This plan is the single source of truth for the MVP. Each part includes a checklist, tests, and success criteria. Target 80% unit test coverage when it is sensible and adds value; prioritize robust integration testing and meaningful unit tests over coverage metrics.

## Part 1: Plan (current)

Checklist
- [x] Review root AGENTS.md and existing documentation.
- [x] Enrich this plan with detailed steps, tests, and success criteria.
- [x] Create frontend/AGENTS.md that documents the existing frontend code.
- [x] Get user approval before starting Part 2.

Tests
- None for this step.

Success criteria
- Plan is detailed, actionable, and approved by the user.
- frontend/AGENTS.md accurately reflects current frontend architecture.

## Part 2: Scaffolding (Docker + FastAPI + scripts)

Checklist
- [x] Define Dockerfile and any compose config needed for local containerized development.
- [x] Create backend FastAPI app in backend/ with a health endpoint and a simple API endpoint.
- [x] Serve a minimal static HTML response at / to validate serving.
- [x] Add scripts in scripts/ for start and stop on Mac, PC, Linux.
- [x] Ensure uv is used as the Python package manager inside the container.
- [x] Add minimal README notes for running locally.

Tests
- [x] Backend unit test for health endpoint.
- [x] Integration test that hits / and the example API endpoint in the running container.

Success criteria
- Container starts with a single command and serves both HTML at / and JSON at the API endpoint.
- Start/stop scripts work on Mac, PC, and Linux (PC/Linux not verified; user approved skip).
- Unit coverage for backend modules at or above 80% (verified at 98%).

## Part 3: Add in Frontend (static build served by backend)

Checklist
- [x] Configure frontend build output for static export compatible with FastAPI serving.
- [x] Update backend to serve the built frontend at /.
- [x] Ensure the Kanban board renders correctly at / in the container.

Tests
- [x] Frontend unit tests continue to pass with coverage targets where sensible.
- [x] Integration test to verify / serves the Kanban UI and key elements exist.

Success criteria
- The app loads the existing Kanban demo at / via the backend.
- All unit and integration tests pass; coverage targets are applied where sensible.

## Part 4: Fake user sign-in experience

Checklist
- [x] Add a simple login screen on / when unauthenticated.
- [x] Hardcode credentials to user/password for MVP.
- [x] Add a logout control that returns to the login screen.
- [x] Preserve Kanban data in memory for the session.

Tests
- [x] Unit tests for login form behavior and validation.
- [x] Integration tests for login, viewing Kanban, and logout flows.

Success criteria
- Unauthenticated users see login screen; authenticated users see Kanban.
- Login and logout flows function reliably with tests covering the flow.

## Part 5: Database modeling

Checklist
- [x] Propose SQLite schema for users, boards, columns, cards, and ordering.
- [x] Save schema proposal as JSON in docs/.
- [x] Document rationale and migration approach in docs/.
- [x] Get user sign-off before implementation.

Tests
- [x] Validate schema JSON structure with a simple unit test.

Success criteria
- Schema proposal is clear, normalized, and approved by the user.

## Part 6: Backend API (persistent Kanban)

Checklist
- [x] Create SQLite DB if missing on startup.
- [x] Implement CRUD endpoints for board, columns, and cards.
- [x] Scope all operations to the signed-in user.
- [x] Add request/response validation and error handling.

Tests
- [x] Unit tests for each endpoint handler (coverage targets where sensible).
- [x] Integration tests for create/read/update/delete card and column flows.

Success criteria
- API persists data to SQLite and passes all tests.
- Coverage targets are applied where sensible for backend units.

## Part 7: Frontend + Backend integration

Checklist
- [x] Replace in-memory Kanban data with backend API calls.
- [x] Add optimistic UI where appropriate.
- [x] Handle error states gracefully.
- [x] Align drag-and-drop identifiers with backend numeric ids via client-side prefixing.
- [x] Route Playwright integration tests through the backend-served frontend.

Tests
- [x] Frontend unit tests updated for API-driven data (coverage targets where sensible).
- [x] Integration tests covering UI + API flows end-to-end.

Success criteria
- Kanban data persists across reloads using the backend.
- Full flow passes integration tests reliably.

Design decisions (Part 7)
- Frontend prefixes backend numeric ids for drag-and-drop stability and strips them before API calls.
- Drag-and-drop uses card/column metadata to resolve drop targets across columns.
- Playwright runs against the backend-served static build to reflect production behavior.

## Part 8: AI connectivity (OpenRouter)

Checklist
- [x] Add backend client that calls OpenRouter with model openai/gpt-oss-120b.
- [x] Read OPENROUTER_API_KEY from .env.
- [x] Implement a simple /api/chat endpoint to verify AI connectivity.
- [x] Hardcode OpenRouter base URL for now.

Notes (Part 8 decisions)
- Use /api/chat for the connectivity endpoint.
- Run a live call to OpenRouter for testing (no mocking).
- Keep the OpenRouter base URL hardcoded.

Tests
- [x] Unit test that returns 500 when OPENROUTER_API_KEY is missing.
- [x] Integration test that validates the "2+2" response path via live OpenRouter (skipped if env is missing).

Success criteria
- OpenRouter connectivity verified with a live response and guarded with tests.

Testing notes (added after Part 8)
- For live integration/E2E tests, start the container in detached mode so the terminal can run tests:
	- docker build -t pm-app .
	- docker rm -f pm-app || true
	- docker run -d --name pm-app --env-file .env -p 8000:8000 pm-app
- Wait for readiness via /health before tests:
	- curl -sf http://127.0.0.1:8000/health
- Backend tests require repo root on PYTHONPATH:
	- PM_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=/absolute/path/to/repo pytest backend
- Frontend tests:
	- npm run test:all (runs unit + Playwright). Playwright uses the backend-served app at 8000.
- Stop the container when done:
	- ./scripts/stop-mac.sh (or platform equivalent)

## Part 9: AI structured outputs for Kanban updates

Checklist
- [ ] Define Structured Output schema for chat responses and optional board updates.
- [ ] Send current Kanban JSON + conversation history to the model.
- [ ] Apply model updates to persisted board data.

Tests
- [ ] Unit tests for schema validation and update application.
- [ ] Integration tests for end-to-end AI update flow (mocked).

Success criteria
- Structured outputs reliably update the Kanban without errors.
- Tests demonstrate correct parsing and persistence.

## Part 10: AI chat sidebar UI

Checklist
- [ ] Build sidebar chat UI aligned to the color scheme.
- [ ] Display conversation history and AI responses.
- [ ] Apply AI-driven Kanban updates and refresh the UI.

Tests
- [ ] Unit tests for chat UI components (coverage targets where sensible).
- [ ] Integration tests for chat flow including AI-triggered Kanban updates (mocked).

Success criteria
- Sidebar chat is responsive, clear, and stable.
- AI-driven Kanban updates reflect immediately in the UI.