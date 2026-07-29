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

Phase 1 was not started.
