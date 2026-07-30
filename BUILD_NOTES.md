# Build Notes

## Phase 0

- The workspace began empty and was not a Git repository.
- The workspace initially blocked `.git` writes, so the first `git init` failed.
  Repository access was subsequently authorized, Phase 0 was committed as
  `cd9f998`, and `main` was pushed to the `abhishek-onewave/daybook_trade`
  repository.
- Python 3.14.6 satisfies the Python 3.11+ requirement.
- Next.js 16.2.12 uses the App Router and plain global CSS; no Tailwind
  dependency is present. The first install used Next.js 14.2.31, but npm marked
  it vulnerable. The scaffold was upgraded to the current stable line before
  verification, including the async route-param and ESLint CLI conventions
  documented for Next.js 16. Sources checked:
  <https://nextjs.org/blog/security-update-2025-12-11> and
  <https://nextjs.org/docs/app/guides/upgrading/version-16>.
- npm's production audit also identified vulnerable transitive `postcss` and
  `sharp` versions beneath Next.js 16.2.12. Package overrides select the current
  patched releases (`postcss` 8.5.25 and `sharp` 0.35.3).
- ESLint 9.39.5 and TypeScript 6.0.3 are used because they are the newest
  releases within `eslint-config-next` 16.2.12's declared peer ranges.
- `npm audit --omit=dev` reports zero production vulnerabilities. The full
  audit reports an upstream `brace-expansion` advisory in ESLint plugin
  tooling. Forcing `brace-expansion` 5 globally breaks legacy `minimatch`
  consumers (`expand is not a function`), and forcing ESLint 10 violates the
  current Next ESLint plugins' peer ranges, so neither unsafe workaround is
  retained.
- SQLite schema changes run through Alembic. The initial migration creates the
  specified tables and seeds NVDA, AAPL, MSFT, TSLA, and AMD.
- Monetary quote fields are stored as decimal strings in the cache schema to
  avoid binary floating-point drift. Phase 1 types and validates upstream
  values before persistence.
- External API documentation was not needed in Phase 0 because no external
  network integration was implemented.
- Phase 1 uses direct Alpaca REST calls through `httpx` rather than
  `alpaca-py`; this keeps feed parameters and defensive payload typing explicit.
- Anthropic model identifiers from the build specification are defined once in
  backend configuration but are not called or independently verified until the
  Chat phase.

## Phase 1

- Alpaca's official API reference was checked on 2026-07-29 before implementing
  the integration. It confirms the multi-symbol snapshot endpoint as
  `GET https://data.alpaca.markets/v2/stocks/snapshots`, with required
  `symbols` and supported `feed=iex` parameters:
  <https://docs.alpaca.markets/us/reference/stocksnapshots-1>.
- The same reference confirms historical bars at
  `GET https://data.alpaca.markets/v2/stocks/bars`, with required `symbols` and
  `timeframe` parameters plus RFC-3339 `start`/`end`, `limit`,
  `adjustment`, `feed`, pagination, and sort controls:
  <https://docs.alpaca.markets/us/v1.4.2/reference/stockbars>.
- Direct asynchronous `httpx` calls were retained instead of `alpaca-py`.
  This makes the explicit free-tier `feed=iex` selection and defensive
  validation of upstream fields visible in the service code.
- The `1M` chart range requests `1Hour` bars across a 45-day lookback. A daily
  mapping would only yield roughly one point per trading session and could not
  satisfy the phase gate's minimum of 50 real points.
- Poll cadence uses the regular weekday 09:30–16:00
  `America/New_York` session window: 15 seconds in-session and 60 seconds
  outside it. A holiday can therefore receive the faster, harmless cadence;
  exchange-calendar precision can be added with the optional Phase 7 streaming
  upgrade.
- Alembic's programmatic startup migration now preserves existing application
  loggers. This keeps Uvicorn startup and runtime failures visible after
  Alembic configures its own logging.
- No specification-versus-documentation deviation was required for the
  snapshot or historical-bars endpoints.
- The production database target changed from the specification's local
  SQLite file to Supabase Postgres for Vercel. SQLite remains only as the
  zero-setup local and test fallback; the SQLAlchemy models and Alembic history
  remain shared.
- Supabase's current SQLAlchemy guidance recommends the Supavisor transaction
  pooler on port 6543 plus SQLAlchemy `NullPool` for serverless deployments.
  Its prepared-statement guidance requires Psycopg's `prepare_threshold=None`
  in transaction mode:
  <https://supabase.com/docs/guides/troubleshooting/using-sqlalchemy-with-supabase-FUqebT>
  and
  <https://supabase.com/docs/guides/troubleshooting/disabling-prepared-statements-qL8lEL>.
- A PostgreSQL-only migration enables RLS without Data API policies on all
  public application tables. The backend owner connection retains access,
  while Supabase `anon` and `authenticated` roles receive none. This remains
  defense in depth even after Supabase's 2026-04-28 change that stops newly
  created public tables from being exposed automatically:
  <https://supabase.com/changelog>.
- PostgreSQL quote writes use one `ON CONFLICT DO UPDATE` statement and reject
  an update older than the stored `as_of`. This makes concurrent request-driven
  refreshes safe across Vercel instances; the in-process lock still avoids
  duplicate refreshes within one instance.
- Vercel deployment uses two stable projects from the same repository: a
  FastAPI project rooted at the repository and a Next.js project rooted at
  `frontend`. Vercel Services was not selected because it remains a private
  beta and is unnecessary for this build:
  <https://vercel.com/docs/monorepos> and
  <https://vercel.com/docs/frameworks/backend/fastapi>.
- Vercel function instances do not run Alembic or the continuous quote poller
  at startup. Schema migration is an explicit release operation, and the
  existing request-driven quote refresh supplies fresh data in serverless
  execution. Local development keeps the required 15/60-second poller.
- The attached Ponytail 4.8.4 development rules were applied in `full` mode:
  existing SQLAlchemy/Alembic and the native Vercel/Next.js features were
  reused, and no Supabase SDK, scheduler replacement, monorepo framework, or
  Ponytail runtime files were added to the product.
