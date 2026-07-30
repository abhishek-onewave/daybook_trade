# Daybook Worklog

Gate evidence is recorded as the command followed by its captured output.

## Phase 0 — Scaffold

Status: **PASS** (2026-07-29)

Implemented:

- FastAPI application with backend-only environment loading.
- Alembic-managed SQLite schema and initial watchlist/settings seed.
- `/api/health` database and configuration status endpoint.
- Next.js App Router shell with shared navigation, all specified routes,
  design tokens, advisory footer, and responsive styling.
- `make backend`, `make frontend`, `make dev`, `make test`, and `make guard`.

### VERIFY — both development servers run

Command:

```text
$ make dev
```

Actual startup output:

```text
.venv/bin/alembic -c backend/alembic.ini upgrade head
cd frontend && npm run dev

> daybook-frontend@0.1.0 dev
> next dev --hostname 0.0.0.0 --port 3000

INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
▲ Next.js 16.2.12 (Turbopack)
- Local:         http://localhost:3000
- Network:       http://0.0.0.0:3000
✓ Ready in 388ms
INFO:     Will watch for changes in these directories: ['/Users/abhi4518/Desktop/onewave/daybook_trade']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [43220] using WatchFiles
INFO:     Started server process [43222]
INFO:     Waiting for application startup.
```

The health request below succeeded against that running Uvicorn process.
Both servers were intentionally stopped after the gate probes completed.

### VERIFY — health endpoint and configuration booleans

Command:

```text
$ curl --fail --silent --show-error http://127.0.0.1:8000/api/health
```

Actual output:

```json
{"status":"ok","as_of":"2026-07-29T23:46:48.209417Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
```

### VERIFY — shared navigation renders on every route

Eight real HTTP fetches were made against the running Next.js server. Each
response was required to exit successfully and contain the server-rendered
primary navigation, brand, route heading, and advisory disclaimer.

Command pattern, run once for each route listed in the output:

```text
$ curl --fail --silent --show-error http://127.0.0.1:3000/<route>
```

Actual output:

```text
/dashboard -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
/news -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
/ask -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
/stats -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
/favorites -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
/portfolio -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
/stock/NVDA -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
/settings -> exit=0; nav=true; brand=true; heading=true; disclaimer=true
```

Next.js request log from the same run:

```text
GET /stats 200 in 1768ms (next.js: 1418ms, application-code: 351ms)
GET /favorites 200 in 1785ms (next.js: 1470ms, application-code: 315ms)
GET /settings 200 in 1791ms (next.js: 1494ms, application-code: 296ms)
GET /portfolio 200 in 1795ms (next.js: 1526ms, application-code: 269ms)
GET /ask 200 in 1807ms (next.js: 1555ms, application-code: 253ms)
GET /dashboard 200 in 1765ms (next.js: 1648ms, application-code: 117ms)
GET /news 200 in 1775ms (next.js: 1723ms, application-code: 52ms)
GET /stock/NVDA 200 in 1852ms (next.js: 1832ms, application-code: 20ms)
```

### Supporting checks

Command:

```text
$ make test
```

Actual output:

```text
.venv/bin/alembic -c backend/alembic.ini upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
.venv/bin/python -m pytest backend/tests
..                                                                       [100%]
2 passed, 1 warning in 0.51s
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ make guard
```

Actual output:

```text
.venv/bin/python -m pytest backend/tests/test_read_only_guard.py
.                                                                        [100%]
1 passed in 0.01s
.venv/bin/ruff check backend
All checks passed!
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ cd frontend && npm run build
```

Actual route output:

```text
Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /ask
├ ○ /dashboard
├ ○ /favorites
├ ○ /news
├ ○ /portfolio
├ ○ /settings
├ ○ /stats
└ ƒ /stock/[sym]

○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```

Command:

```text
$ sqlite3 data/daybook.db '.tables'
$ sqlite3 data/daybook.db 'select symbol,name from watchlist order by symbol;'
```

Actual output:

```text
alembic_version      portfolio_snapshots  usage_log
conversations        quotes_cache         watchlist
messages             settings
news_items           tt_tokens
AAPL|Apple
AMD|Advanced Micro Devices
MSFT|Microsoft
NVDA|NVIDIA
TSLA|Tesla
```

Command:

```text
$ cd frontend && npm audit --omit=dev
```

Actual output:

```text
found 0 vulnerabilities
```

At the time this Phase 0 gate was recorded, Phase 1 had not been started.

## Phase 1 — Quotes

Status: **BLOCKED — VERIFY gate not passed** (2026-07-29)

Implemented:

- Direct asynchronous Alpaca REST snapshots and historical bars with
  `feed=iex`, defensive finite-number validation, and backend-only credentials.
- Eight-symbol snapshot polling (NVDA, AAPL, MSFT, TSLA, AMD, SPY, QQQ, DIA)
  every 15 seconds during the regular weekday session and every 60 seconds
  off-hours, persisted to `quotes_cache`.
- `/api/prices` and `/api/bars` with timestamps, structured unavailable states,
  and a `1M` hourly-bars mapping designed to exceed 50 real chart points.
- Dashboard watchlist, broad-market tiles, Stats table, and live tape with
  loading, retry, partial-data, delayed, as-of, indicative-IEX, and honest
  unavailable states. All display formatters reject non-finite values.
- Supabase Postgres support through Psycopg, the port-6543 transaction pooler,
  `NullPool`, disabled prepared statements, and a PostgreSQL-only RLS migration.
- A Vercel FastAPI entrypoint and serverless mode that skips runtime migrations
  and the continuous poller, while retaining request-driven quote refresh.
- A PostgreSQL atomic quote upsert that prevents an older concurrent response
  from overwriting a newer cached quote.

Phase 2 has not been started. The implementation and offline checks are green,
but the required real-data gate cannot pass because the private `.env` does not
contain Alpaca credentials.

### VERIFY attempt — prices

Command:

```text
$ curl --silent --show-error --write-out '\nHTTP %{http_code}\n' http://127.0.0.1:8000/api/prices
```

Actual output:

```text
{"as_of":"2026-07-30T00:27:00.990201Z","feed":"iex","status":"unavailable","market_open":false,"quotes":{},"indices":{},"error":{"code":"MARKET_DATA_UNAVAILABLE","message":"Alpaca credentials are not configured."}}
HTTP 503
```

Gate result: **BLOCKED**. This is an honest unavailable response, not real
numeric data for the eight required symbols.

### VERIFY attempt — NVDA one-month bars

Command:

```text
$ curl --silent --show-error --write-out '\nHTTP %{http_code}\n' 'http://127.0.0.1:8000/api/bars?symbol=NVDA&range=1M'
```

Actual output:

```text
{"as_of":"2026-07-30T00:27:07.815065Z","feed":"iex","status":"unavailable","market_open":false,"error":{"code":"MARKET_DATA_NOT_CONFIGURED","message":"Alpaca credentials are not configured."}}
HTTP 503
```

Gate result: **BLOCKED**. No real bar points were available without
credentials.

### Supporting checks — hydrated UI unavailable state

A real headless Chromium session loaded each page after client hydration and
checked the rendered text for its retryable error row, honest unavailable
copy, IEX label, and any literal `NaN`.

Actual output:

```json
{"route":"/dashboard","error_row":true,"honest_unavailable":true,"indicative_iex":true,"has_nan":false}
{"route":"/stats","error_row":true,"honest_unavailable":true,"indicative_iex":true,"has_nan":false}
```

This proves the failure state is honest and contains no `NaN`; it does **not**
satisfy the live-values UI gate.

### Supporting checks — backend, guard, and frontend

Command:

```text
$ make test
```

Relevant actual output:

```text
.venv/bin/python -m pytest backend/tests
............                                                             [100%]
12 passed, 1 warning in 0.38s
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ make guard
```

Relevant actual output:

```text
.venv/bin/python -m pytest backend/tests/test_read_only_guard.py
.                                                                        [100%]
1 passed in 0.01s
.venv/bin/ruff check backend
All checks passed!
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ cd frontend && npm run build
```

Relevant actual output:

```text
✓ Compiled successfully in 1402ms
✓ Generating static pages using 7 workers (10/10) in 111ms

Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /ask
├ ○ /dashboard
├ ○ /favorites
├ ○ /news
├ ○ /portfolio
├ ○ /settings
├ ○ /stats
└ ƒ /stock/[sym]
```

### Supporting checks — Supabase and Vercel adaptation

No existing connected Supabase project is identified as Daybook, so no remote
database was selected or mutated. The migration was instead generated against
PostgreSQL offline and inspected before a dedicated project is connected.

Command:

```text
$ make test
```

Relevant actual output after the platform adaptation:

```text
.venv/bin/python -m pytest backend/tests
.................                                                        [100%]
17 passed, 1 warning in 0.39s
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ make guard
```

Actual output:

```text
.venv/bin/python -m pytest backend/tests/test_read_only_guard.py
.                                                                        [100%]
1 passed in 0.01s
.venv/bin/ruff check backend
All checks passed!
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ DATABASE_URL='postgresql://postgres:test@localhost:6543/postgres?sslmode=require' \
  .venv/bin/alembic -c backend/alembic.ini upgrade head --sql
```

Relevant actual output:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Generating static SQL
ALTER TABLE "alembic_version" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "conversations" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "messages" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "watchlist" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "news_items" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "quotes_cache" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "tt_tokens" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "portfolio_snapshots" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "settings" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "usage_log" ENABLE ROW LEVEL SECURITY;
UPDATE alembic_version SET version_num='0002_supabase_rls'
WHERE alembic_version.version_num = '0001_phase_0';
```

Command:

```text
$ DATABASE_URL='postgresql://postgres:test@localhost:6543/postgres?sslmode=require' \
  .venv/bin/python -c '<inspect SQLAlchemy engine>'
```

Actual output:

```text
{'driver': 'psycopg', 'pool': 'NullPool', 'url': 'postgresql+psycopg://postgres:***@localhost:6543/postgres?sslmode=require'}
```

Command:

```text
$ VERCEL=1 DAYBOOK_API_ORIGIN=https://daybook-api.example.com/ \
  node '<load frontend/next.config.mjs and print rewrites>'
```

Actual output:

```json
[{"source":"/api/:path*","destination":"https://daybook-api.example.com/api/:path*"}]
```

The same check without `DAYBOOK_API_ORIGIN` failed with the intended
`DAYBOOK_API_ORIGIN is required on Vercel.` configuration error.

Command:

```text
$ VERCEL=1 \
  DATABASE_URL='postgresql://postgres:test@localhost:6543/postgres?sslmode=require' \
  .venv/bin/python -c '<import root Vercel app>'
```

Actual output:

```text
{'title': 'Daybook API', 'vercel_entrypoint': True}
```

Command:

```text
$ cd frontend && npm run build
```

Relevant actual output:

```text
✓ Compiled successfully in 1382ms
✓ Generating static pages using 7 workers (10/10) in 138ms

Route (app)
┌ ○ /
├ ○ /_not-found
├ ○ /ask
├ ○ /dashboard
├ ○ /favorites
├ ○ /news
├ ○ /portfolio
├ ○ /settings
├ ○ /stats
└ ƒ /stock/[sym]
```

### VERIFY re-attempt after platform adaptation

Command:

```text
$ curl --fail --silent --show-error http://127.0.0.1:8000/api/health
```

Actual output:

```json
{"status":"ok","as_of":"2026-07-30T00:53:28.829747Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
```

Commands:

```text
$ curl --silent --show-error --write-out '\nHTTP %{http_code}\n' http://127.0.0.1:8000/api/prices
$ curl --silent --show-error --write-out '\nHTTP %{http_code}\n' \
  'http://127.0.0.1:8000/api/bars?symbol=NVDA&range=1M'
```

Actual output:

```text
{"as_of":"2026-07-30T00:53:28.850918Z","feed":"iex","status":"unavailable","market_open":false,"quotes":{},"indices":{},"error":{"code":"MARKET_DATA_UNAVAILABLE","message":"Alpaca credentials are not configured."}}
HTTP 503
{"as_of":"2026-07-30T00:53:28.860550Z","feed":"iex","status":"unavailable","market_open":false,"error":{"code":"MARKET_DATA_NOT_CONFIGURED","message":"Alpaca credentials are not configured."}}
HTTP 503
```

Gate result remains **BLOCKED**. Supabase/Vercel compatibility is supported by
real local and generated-SQL evidence, but the Phase 1 gate still requires a
deployed or local environment containing real Alpaca credentials. Phase 2 has
not been started.

### Security and deployment follow-up

The Vercel adaptation was independently reviewed and hardened before commit.
This supersedes the earlier external `next.config.mjs` rewrite with a
credential-injecting server-side route:

- Every PostgreSQL URL, including the direct/session-pooler migration URL,
  receives `sslmode=require` when absent and rejects weaker modes.
- `APP_ENVIRONMENT=production` is an app-owned serverless marker; the
  production API requires Supabase's port-6543 transaction pooler and rejects
  SQLite. PostgreSQL-backed or explicitly token-configured local API runs also
  enforce the internal token.
- The Web deployment uses HTTPS Basic authentication and a server-side
  `/api/[...path]` gateway. Browser `Authorization`, cookies, and forged
  Daybook tokens are removed before the configured internal token is added.
- Production rejects plain HTTP, an HTTP API origin, weak or absent secrets,
  cross-origin API redirects, and backend `Set-Cookie` leakage. Same-origin
  redirects remain inside the authenticated Web gateway.
- Unsafe gateway methods fail closed unless browser origin metadata is exactly
  same-origin, preventing later mutation routes from inheriting Basic-auth
  CSRF exposure.

Command:

```text
$ make test
```

Actual output:

```text
.venv/bin/alembic -c backend/alembic.ini upgrade head
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
.venv/bin/python -m pytest backend/tests
......................                                                   [100%]
22 passed, 1 warning in 0.45s
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ make guard
```

Actual output:

```text
.venv/bin/python -m pytest backend/tests/test_read_only_guard.py
.                                                                        [100%]
1 passed in 0.01s
.venv/bin/ruff check backend
All checks passed!
cd frontend && npm run lint

> daybook-frontend@0.1.0 lint
> eslint .
```

Command:

```text
$ cd frontend
$ DAYBOOK_API_ORIGIN=https://api.example.test \
  DAYBOOK_API_TOKEN=<test-only-token> \
  DAYBOOK_ACCESS_PASSWORD=<test-only-password> npm run build
```

Relevant actual output:

```text
✓ Compiled successfully in 1363ms
✓ Finished TypeScript in 1340ms
✓ Generating static pages using 7 workers (10/10) in 141ms

Route (app)
┌ ○ /
├ ○ /_not-found
├ ƒ /api/[...path]
├ ○ /ask
├ ○ /dashboard
├ ○ /favorites
├ ○ /news
├ ○ /portfolio
├ ○ /settings
├ ○ /stats
└ ƒ /stock/[sym]

ƒ Proxy (Middleware)
```

Command:

```text
$ DATABASE_URL='postgresql://postgres:test@db.example:5432/postgres' \
  .venv/bin/python -c '<print normalized SQLAlchemy URL>'
```

Actual output:

```text
postgresql+psycopg://postgres:test@db.example:5432/postgres?sslmode=require
```

Two real local servers were then started with separate test-only Web and API
credentials. The values are redacted below.

Command:

```text
$ curl --silent --show-error --write-out '\nHTTP %{http_code}\n' \
  http://127.0.0.1:3000/api/health
```

Actual output:

```text
Authentication required.
HTTP 401
```

Command:

```text
$ curl --silent --show-error --location \
  --user 'daybook:<test-only-password>' \
  --header 'x-daybook-api-token: browser-forged-token' \
  --write-out '\nHTTP %{http_code}\n' \
  http://127.0.0.1:3000/api/health/
```

Actual output:

```text
{"status":"ok","as_of":"2026-07-30T01:27:53.388476Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
HTTP 200
```

This successful response proves the gateway replaced the forged browser token
with its server-only credential and kept the redirect on the Web origin.

Command:

```text
$ curl --silent --show-error --write-out '\nHTTP %{http_code}\n' \
  http://127.0.0.1:8000/api/health
```

Actual output:

```text
{"detail":"Unauthorized."}
HTTP 401
```

Commands:

```text
$ curl --silent --show-error --request POST \
  --user 'daybook:<test-only-password>' \
  --header 'origin: https://evil.example' \
  --header 'sec-fetch-site: cross-site' \
  --write-out '\nHTTP %{http_code}\n' \
  http://127.0.0.1:3000/api/health
$ curl --silent --show-error --request POST \
  --user 'daybook:<test-only-password>' \
  --header 'origin: http://127.0.0.1:3000' \
  --header 'sec-fetch-site: same-origin' \
  --write-out '\nHTTP %{http_code}\n' \
  http://127.0.0.1:3000/api/health
```

Actual output:

```text
{"detail":"Cross-site request blocked."}
HTTP 403

{"detail":"Method Not Allowed"}
HTTP 405
```

The same-origin control reached FastAPI and received its expected `405`
because `/api/health` is GET-only; the cross-site request was rejected by the
Web gateway and never reached FastAPI.

The optimized production Web server was also probed over local HTTP. It failed
closed at both transport boundaries:

```text
HTTPS is required.
HTTP 426

{"detail":"Service unavailable."}
HTTP 503
```

The first response rejected a plain-HTTP Web request. The second request
simulated Vercel's HTTPS forwarding header but deliberately configured an HTTP
API origin; the gateway rejected it before sending the internal token.

Gate result remains **BLOCKED**. These checks pass the Supabase/Vercel security
checkpoint, but they do not supply the real Alpaca quote and bar output required
by Phase 1 VERIFY. Phase 2 has not been started.

### Vercel build repair and project split

The user-created `one-wave/daybook-trade` project was inspected after its
first Git deployment failed.

Command:

```text
$ vercel inspect https://daybook-trade-hmvgrru5v-one-wave.vercel.app \
  --logs --scope one-wave
```

Actual failure:

```text
Failed to parse "requirements.txt". File content:
-r backend/requirements.txt
Error: could not parse requirements.txt: Error parsing included file
```

The root runtime manifest was changed to list production dependencies directly
and `.python-version` was set to `3.12`. A real Vercel preview build then
completed:

```text
Using Python 3.12 from .python-version
Using uv 0.10.11
Installing required dependencies from requirements.txt...
Compiling Python bytecode...
Build Completed in /vercel/output [4s]
Deployment completed
status  ● Ready
```

The preview health request deliberately failed closed because the Vercel
project still has no environment variables:

```text
$ vercel curl /api/health \
  --deployment https://daybook-trade-o82puzmth-one-wave.vercel.app

A server error has occurred
FUNCTION_INVOCATION_FAILED
HTTP 500
```

The corresponding real runtime log identifies the missing deployment
configuration rather than an application-code regression:

```text
ValueError: DATABASE_URL must use Supabase Postgres in production.
```

The API-only Vercel project could not serve the Next.js application. A second
Git-connected project, `one-wave/daybook-trade-web`, was therefore created
with Root Directory `frontend` and Framework Preset `Next.js`. Its production
build succeeded:

```text
Detected Next.js version: 16.2.12
✓ Compiled successfully in 3.0s
Finished TypeScript in 2.6s
✓ Generating static pages using 3 workers (10/10) in 220ms

Route (app)
┌ ○ /
├ ○ /_not-found
├ ƒ /api/[...path]
├ ○ /ask
├ ○ /dashboard
├ ○ /favorites
├ ○ /news
├ ○ /portfolio
├ ○ /settings
├ ○ /stats
└ ƒ /stock/[sym]

ƒ Proxy (Middleware)
Build Completed in /vercel/output [20s]
✓ Ready in 34s
Aliased https://daybook-trade-web.vercel.app
```

Gate result remains **BLOCKED**. Both Vercel runtimes now build, but neither
project has environment variables, no dedicated Daybook Supabase project
exists in the connected account, and the Phase 1 gate still lacks real Alpaca
quote/bar output. Phase 2 has not been started.

### Zero-credential Vercel preview

An explicit `DAYBOOK_DEMO_MODE=true` path was added so the application can be
inspected before Supabase or provider credentials are configured. In deployed
demo mode the API migrates a temporary `/tmp/daybook-demo.db`, skips provider
pollers and authentication secrets, labels health output as demo, and refuses
to connect to a Postgres URL. The Web project displays a preview banner and
keeps missing integration data unavailable rather than generating sample
market values.

Automated verification:

```text
$ make test
..........................                                               [100%]
26 passed, 1 warning in 0.47s

$ make guard
.                                                                        [100%]
1 passed in 0.01s
All checks passed!

$ cd frontend && npm run build
✓ Compiled successfully in 1577ms
Finished TypeScript in 1278ms
✓ Generating static pages using 7 workers (10/10) in 155ms
```

The production API deployment completed with:

```text
Using Python 3.12 from .python-version
Installing required dependencies from requirements.txt...
Compiling Python bytecode...
Build Completed in /vercel/output [3s]
Deployment completed
Aliased https://daybook-trade.vercel.app
Ready in 25s
```

Real public API checks:

```text
$ curl https://daybook-trade.vercel.app/api/health
{"status":"ok","mode":"demo","as_of":"2026-07-30T02:20:32.428526Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
HTTP 200

$ curl https://daybook-trade.vercel.app/api/prices
{"as_of":"2026-07-30T02:20:32.768632Z","feed":"iex","status":"unavailable","market_open":false,"quotes":{},"indices":{},"error":{"code":"MARKET_DATA_UNAVAILABLE","message":"Alpaca credentials are not configured."}}
HTTP 503
```

The production Web deployment completed with:

```text
Detected Next.js version: 16.2.12
✓ Compiled successfully in 3.4s
Finished TypeScript in 2.9s
✓ Generating static pages using 3 workers (10/10) in 261ms
Build Completed in /vercel/output [10s]
Deployment completed
Aliased https://daybook-trade-web.vercel.app
Ready in 28s
```

Real public Web and Web-gateway checks:

```text
$ curl https://daybook-trade-web.vercel.app/
WEB / HTTP 200
Preview mode · Live market, AI, brokerage, and Supabase connections are not configured.

$ curl https://daybook-trade-web.vercel.app/api/health
{"status":"ok","mode":"demo","as_of":"2026-07-30T02:21:47.556301Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
HTTP 200

$ curl https://daybook-trade-web.vercel.app/api/prices
{"as_of":"2026-07-30T02:21:47.951137Z","feed":"iex","status":"unavailable","market_open":false,"quotes":{},"indices":{},"error":{"code":"MARKET_DATA_UNAVAILABLE","message":"Alpaca credentials are not configured."}}
HTTP 503
```

The zero-credential preview is **PASS** and the app shell is publicly
inspectable. The Phase 1 gate remains **BLOCKED** because its contract requires
real Alpaca quote/bar values; Phase 2 has not been started.

### Unified Vercel Services deployment

The two-project deployment was consolidated into the single existing
`one-wave/daybook-trade-web` project. `vercel.json` now defines a public
Next.js `frontend` service with a private binding to a FastAPI `backend`
service. Only the frontend has a public rewrite; browser `/api/*` requests
continue through the authenticated Next.js gateway before it calls FastAPI
over the deployment-aware internal binding.

The Vercel project Root Directory was changed from `frontend` to the repository
root and its Framework Preset was changed from `nextjs` to `services`.
`DAYBOOK_API_ORIGIN` was removed because Vercel now injects
`DAYBOOK_BACKEND_URL` for the private binding.

Real local Vercel Services startup:

```text
$ DAYBOOK_DEMO_MODE=true npx --yes vercel@58.1.0 dev -L \
    --listen 3005 --project daybook-trade-web --scope one-wave --yes
Detected services:
• frontend  [Next.js]
• backend   [FastAPI]
> Available at:
  http://localhost:3005
[frontend] ✓ Ready in 372ms
[backend] INFO: Uvicorn running
[backend] INFO: Application startup complete.
```

Real local unified-route checks:

```text
$ curl --location http://127.0.0.1:3005/
WEB HTTP 200

$ curl http://127.0.0.1:3005/api/health
{"status":"ok","mode":"demo","as_of":"2026-07-30T03:05:01.528696Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
HEALTH HTTP 200

$ curl http://127.0.0.1:3005/api/prices
{"as_of":"2026-07-30T03:05:01.564072Z","feed":"iex","status":"unavailable","market_open":false,"quotes":{},"indices":{},"error":{"code":"MARKET_DATA_UNAVAILABLE","message":"Alpaca credentials are not configured."}}
PRICES HTTP 503
```

The first unified production build completed both service builds in one
deployment:

```text
Detected Next.js version: 16.2.12
✓ Compiled successfully in 3.3s
Finished TypeScript in 2.7s
✓ Generating static pages using 3 workers (10/10) in 279ms
Using Python 3.12 from backend/.python-version
Installing required dependencies from pyproject.toml...
Compiling Python bytecode...
Build Completed in /vercel/output [25s]
Aliased https://daybook-trade-web.vercel.app
Ready in 43s
```

Real production checks through the single public project:

```text
$ curl --location https://daybook-trade-web.vercel.app/
WEB HTTP 200

$ curl https://daybook-trade-web.vercel.app/api/health
{"status":"ok","mode":"demo","as_of":"2026-07-30T03:08:39.002253Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
HEALTH HTTP 200

$ curl https://daybook-trade-web.vercel.app/api/prices
{"as_of":"2026-07-30T03:08:41.097807Z","feed":"iex","status":"unavailable","market_open":false,"quotes":{},"indices":{},"error":{"code":"MARKET_DATA_UNAVAILABLE","message":"Alpaca credentials are not configured."}}
PRICES HTTP 503
```

The one-project deployment checkpoint is **PASS**. The Phase 1 gate remains
**BLOCKED** because its contract requires real Alpaca quote/bar values; Phase 2
has not been started.

The Git-driven deployment for commit `8b00566` was then verified after
`DAYBOOK_API_ORIGIN` had been removed:

```text
status  ● Ready

Builds
├── λ services/backend/fastapi (32.37MB) [iad1]
├── λ services/frontend/index (674.5KB) [iad1]
└── 73 output items hidden

$ curl https://daybook-trade-web.vercel.app/api/health
{"status":"ok","mode":"demo","as_of":"2026-07-30T03:13:13.939524Z","database":{"configured":true,"connected":true},"integrations":{"anthropic_configured":false,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":false},"tastytrade_environment":"sandbox"}
HEALTH HTTP 200
```

The obsolete project was removed only after that final binding check:

```text
$ vercel project remove daybook-trade --scope one-wave
Success! Project daybook-trade removed

$ vercel project list --scope one-wave
daybook-trade-web  https://daybook-trade-web.vercel.app
```

The removed Vercel project and its historical deployments are not recoverable
through this workspace. The Git repository and retained
`daybook-trade-web` deployment contain the complete application source.

## Cross-cutting checkpoint — independent provider configuration (2026-07-29)

Goal: keep the application available when any provider credentials are absent,
detect newly configured credentials independently, and never claim an
unimplemented integration is ready.

Implementation:

- Demo/preview mode now ignores configured Supabase and provider credentials,
  uses temporary SQLite on Vercel, and never starts the Alpaca poller.
- Live mode evaluates Alpaca, Anthropic, Finnhub, and Tastytrade independently.
  A missing provider only disables that provider.
- `/api/health` reports configuration, enablement, implementation, and state for
  each provider. The Settings page renders the same capability states.
- Alpaca refresh returns a provider-specific unavailable response when its
  credentials are missing or preview mode disables it.
- Anthropic, Finnhub, and Tastytrade are reported as pending rather than ready
  because their gated implementation phases have not started.

Real local verification:

```text
$ make test
27 passed, 1 warning

$ make guard
1 passed
All checks passed!

$ cd frontend && npm run lint
eslint .

$ cd frontend && npm run build
✓ Compiled successfully
✓ Finished TypeScript
✓ Generating static pages (10/10)
```

With `DAYBOOK_DEMO_MODE=false` but the required application access credentials
absent, the first production deployment correctly failed closed:

```text
$ curl https://daybook-trade-web.vercel.app/api/health
Service unavailable.
HTTP 503

$ curl https://daybook-trade-web.vercel.app/settings
HTTP 503
```

No provider or application secret value was printed. Production preview mode
was restored with `DAYBOOK_DEMO_MODE=true`, and the unified project was
redeployed successfully:

```text
Deployment https://daybook-trade-fixe6pkv7-one-wave.vercel.app
Aliased https://daybook-trade-web.vercel.app
Ready in 34s

$ curl https://daybook-trade-web.vercel.app/api/health
{"status":"ok","mode":"demo","as_of":"2026-07-30T05:23:13.386926Z","database":{"configured":true,"connected":true,"persistent":false},"integrations":{"anthropic_configured":true,"alpaca_configured":false,"tastytrade_configured":false,"finnhub_configured":true},"capabilities":{"anthropic":{"configured":true,"enabled":false,"implemented":false,"state":"disabled_in_demo"},"alpaca":{"configured":false,"enabled":false,"implemented":true,"state":"not_configured"},"tastytrade":{"configured":false,"enabled":false,"implemented":false,"state":"not_configured"},"finnhub":{"configured":true,"enabled":false,"implemented":false,"state":"disabled_in_demo"}},"tastytrade_environment":"sandbox"}
HTTP 200

$ curl https://daybook-trade-web.vercel.app/settings
HTTP 200

$ curl https://daybook-trade-web.vercel.app/api/prices
{"as_of":"2026-07-30T05:23:15.796410Z","feed":"iex","status":"unavailable","market_open":false,"quotes":{},"indices":{},"error":{"code":"MARKET_DATA_UNAVAILABLE","message":"Alpaca credentials are not configured."}}
HTTP 503
```

This cross-cutting availability checkpoint is **PASS**. Phase 1 remains
**BLOCKED** because its VERIFY gate requires real Alpaca quote/bar values.
Phase 2 has not been started, in accordance with G10.
