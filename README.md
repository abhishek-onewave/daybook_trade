# Daybook

Daybook is Tracy's single-user stock-research application. The current build
provides the FastAPI/SQLAlchemy foundation, the Next.js application shell, and
Alpaca-backed IEX quotes and historical bars. Production persistence targets
Supabase Postgres; SQLite remains the local development and test fallback.
News, chat, and the read-only brokerage connection remain deliberately absent
until their gated phases.

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

`/api/health` reports whether each credential pair is configured without
disclosing credential values.

## Supabase database

Use a dedicated Supabase project for Daybook. In its **Connect** panel, copy
the transaction-pooler connection string on port `6543`, require SSL, and set
it as the backend's `DATABASE_URL`. Keep that URL backend-only; it contains the
database password.

Before the first deployment, put the Supabase URL in the private root `.env`
and apply the schema once:

```bash
make migrate
```

The migration enables row-level security on every public Daybook table and
defines no anonymous or authenticated Data API policies. Daybook connects
directly from FastAPI as the database owner; no Supabase key or database
credential belongs in the frontend.

## Vercel deployment

Create two Vercel projects from this repository:

| Project | Root directory | Required environment |
| --- | --- | --- |
| Daybook API | `.` | `DATABASE_URL`, `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`, and later-phase backend secrets |
| Daybook Web | `frontend` | `DAYBOOK_API_ORIGIN=https://<daybook-api-domain>` |

Deploy the API first, set its stable HTTPS domain in the Web project, and then
deploy the Web project. The browser continues to call relative `/api/*` URLs;
Next.js proxies those requests to the API without exposing backend secrets or
requiring production CORS.

Vercel sets `VERCEL=1` automatically. In that runtime Daybook does not run
Alembic or a continuous background poller during function startup. Quotes
refresh on demand through `/api/prices`, while local development retains the
specified 15/60-second poller.

After both deployments:

```bash
curl https://<daybook-api-domain>/api/health
curl https://<daybook-web-domain>/api/prices
curl 'https://<daybook-web-domain>/api/bars?symbol=NVDA&range=1M'
```

Log the actual responses in `WORKLOG.md`; Phase 1 passes only when those calls
and the deployed UI show real Alpaca values. The application does not yet have
a user-authentication layer, so keep deployments private until a single-user
access gate exists—especially before portfolio or chat data is added.

## Alpaca market data

Set `ALPACA_API_KEY_ID` and `ALPACA_API_SECRET_KEY` in the private `.env` file.
Daybook calls Alpaca's Market Data REST API directly with `httpx`; no market
credentials are sent to the browser.

- `GET /api/prices` serves cached snapshots for NVDA, AAPL, MSFT, TSLA, AMD,
  SPY, QQQ, and DIA.
- `GET /api/bars?symbol=NVDA&range=1M` serves chart-ready historical bars.
- The backend refreshes snapshots every 15 seconds during regular US market
  hours and every 60 seconds outside them.

Quotes and bars explicitly request Alpaca's free `iex` feed. Values are
therefore labeled **Indicative (IEX)** in the interface and are not a
consolidated SIP view. Alpaca's paid Algo Trader Plus market-data subscription
is the documented upgrade path for full SIP coverage; it is not required for
Daybook v1.
