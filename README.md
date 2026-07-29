# Daybook

Daybook is Tracy's single-user stock-research application. Phase 0 provides the
FastAPI/SQLite foundation and the Next.js application shell. Market data, news,
chat, and the read-only brokerage connection remain deliberately absent until
their gated phases.

Daybook explains markets. It doesn't recommend trades.

## Requirements

- Python 3.11 or newer
- Node.js 18.17 or newer
- GNU Make

## Local setup

```bash
cp .env.example .env
make setup
make dev
```

The frontend runs at <http://localhost:3000>. The API runs at
<http://localhost:8000>; its OpenAPI UI is at
<http://localhost:8000/api/docs>.

`make dev` applies pending Alembic migrations before starting FastAPI. The
default SQLite database is `data/daybook.db`.

## Checks

```bash
make test
make guard
```

`make guard` includes the automated read-only brokerage mutation check. No
brokerage order placement, modification, or cancellation is in scope.

## Configuration

Copy `.env.example` to `.env` and keep the resulting file private. API keys and
broker tokens are backend-only and are never exposed through the Next.js
environment.

Upstream services are not called in Phase 0. `/api/health` reports whether each
credential pair is configured without disclosing credential values.

