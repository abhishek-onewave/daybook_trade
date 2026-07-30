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

Use a dedicated Supabase project for Daybook. It provides two connection URLs
for two different jobs:

- **Vercel runtime:** use the transaction-pooler URL on port `6543` as the API
  project's `DATABASE_URL`. Daybook adds `sslmode=require` when absent and
  rejects weaker TLS modes. For certificate and hostname verification, install
  the project's CA certificate and use `sslmode=verify-full`.
- **Migrations:** use the direct connection URL on port `5432` in the private
  local `.env`. If the migration machine cannot reach Supabase over IPv6, use
  the session-pooler URL on port `5432` instead. Do not run Alembic through the
  transaction pooler. Daybook enforces the same TLS rule for this URL.

Before the first deployment, set the migration URL locally and apply the
schema once:

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
| Daybook API | `.` | `APP_ENVIRONMENT=production`, `DATABASE_URL`, `DAYBOOK_API_TOKEN`, `ALPACA_API_KEY_ID`, `ALPACA_API_SECRET_KEY`, and later-phase backend secrets |
| Daybook Web | `frontend` | `DAYBOOK_API_ORIGIN=https://<daybook-api-domain>`, the same `DAYBOOK_API_TOKEN`, and `DAYBOOK_ACCESS_PASSWORD` |

Deploy the API first, set its stable HTTPS domain in the Web project, and then
deploy the Web project. Generate separate strong values for the internal API
token and the human access password:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

The Web project requires HTTP Basic authentication over HTTPS (username
`daybook`, password `DAYBOOK_ACCESS_PASSWORD`) and proxies relative `/api/*`
requests server-side. The proxy adds `DAYBOOK_API_TOKEN`; direct API requests
without that token are rejected. Neither secret is exposed through a
`NEXT_PUBLIC_` variable. Unsafe Web gateway methods also require an exact
same-origin `Origin` header so later write routes cannot inherit Basic-auth
CSRF exposure. Vercel Authentication on **All Deployments** can be
enabled as an additional platform-level gate on the **Web project only** when
the account plan supports it. Leave that platform gate off on the API project:
the cross-project Web gateway authenticates to FastAPI with
`DAYBOOK_API_TOKEN`, not a Vercel Authentication cookie or bypass secret.

`APP_ENVIRONMENT=production` is an app-owned deployment marker, so security
does not depend on Vercel's optional system-environment exposure setting.
Production rejects SQLite, requires the port-6543 transaction pooler, TLS, and
the internal API token; Supabase-backed local API runs require the token too.
Production does not run Alembic or a continuous background poller during
function startup. Quotes refresh on demand through `/api/prices`, while local
SQLite development retains the specified 15/60-second poller.

After both deployments:

```bash
curl -H "x-daybook-api-token: $DAYBOOK_API_TOKEN" \
  https://<daybook-api-domain>/api/health
curl -u "daybook:$DAYBOOK_ACCESS_PASSWORD" \
  https://<daybook-web-domain>/api/prices
curl -u "daybook:$DAYBOOK_ACCESS_PASSWORD" \
  'https://<daybook-web-domain>/api/bars?symbol=NVDA&range=1M'
```

Log the actual responses in `WORKLOG.md`; Phase 1 passes only when those calls
and the deployed UI show real Alpaca values. Basic authentication is the
deliberately small single-user gate for v1; replace it with managed identity
and session auth before Daybook ever becomes multi-user.

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
