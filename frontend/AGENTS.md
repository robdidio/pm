# Frontend Demo Overview

## Purpose

This frontend is a standalone NextJS demo of a single-board Kanban experience. It is currently frontend-only and uses in-memory state.

## Tech Stack

- NextJS App Router
- React 19
- Tailwind CSS v4 (via @tailwindcss/postcss)
- Drag and drop with @dnd-kit
- Testing: Vitest + React Testing Library, Playwright for E2E

## Structure

- src/app/layout.tsx: App shell, fonts, metadata.
- src/app/page.tsx: Renders the Kanban board.
- src/app/globals.css: Theme variables and base styles.
- src/components/KanbanBoard.tsx: Board container, drag-and-drop state, and handlers.
- src/components/KanbanColumn.tsx: Column UI, droppable area, renaming, and card list.
- src/components/KanbanCard.tsx: Sortable card item.
- src/components/KanbanCardPreview.tsx: Drag overlay preview card.
- src/components/NewCardForm.tsx: Add-card form.
- src/lib/kanban.ts: Board types, initial data, moveCard logic, id creation.

## Current Behaviors

- Five fixed columns rendered from initial data.
- Columns are renameable.
- Cards can be added, deleted, and moved with drag and drop.
- All data is stored in React state (no persistence).

## Tests

- src/components/KanbanBoard.test.tsx: Renders columns, renames, adds/deletes cards.
- src/lib/kanban.test.ts: moveCard behavior across columns and order.

## Scripts

- npm run dev: NextJS dev server.
- npm run build: NextJS production build.
- npm run start: NextJS production server.
- npm run test: Vitest tests.
- npm run test:e2e: Playwright tests.
