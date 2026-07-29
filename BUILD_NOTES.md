# Build Notes

## Phase 0

- The workspace began empty and was not a Git repository.
- The phase specification asks for a commit per phase, but `.git` is mounted
  read-only in this workspace. `git init` returned
  `/Users/abhi4518/Desktop/onewave/daybook_trade/.git: Operation not permitted`,
  so no Phase 0 commit could be created.
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
  avoid binary floating-point drift. Phase 1 will type and validate upstream
  values before persistence.
- External API documentation was not needed in Phase 0 because no external
  network integration was implemented.
- Phase 1 will use direct Alpaca REST calls through `httpx` rather than
  `alpaca-py`; this keeps feed parameters and defensive payload typing explicit.
- Anthropic model identifiers from the build specification are defined once in
  backend configuration but are not called or independently verified until the
  Chat phase.
