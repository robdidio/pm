# Database approach

## Storage choice

- SQLite for local persistence.
- One board per user for the MVP, but schema supports multiple users and boards.

## Relational model

See docs/DB_SCHEMA_RELATIONAL.json for table definitions, foreign keys, and indexes.

Notes:
- Columns and cards use a position integer for ordering within their parent.
- Cards store both board_id and column_id for fast filtering and integrity.
- Timestamps are stored as ISO-8601 text strings for simplicity.

## Document model

See docs/DB_SCHEMA_DOCUMENT.json for a single-document aggregate shape.

Notes:
- The board document contains columns and a cards map.
- Column cardIds define ordering and placement.
- Card objects include columnId for fast validation and updates.

## Initialization

- Create the database file on startup if it does not exist.
- Run schema creation with IF NOT EXISTS guards.
- Seed a single board for a user on first run if no data exists.
