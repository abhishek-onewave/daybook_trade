"use client";

import Link from "next/link";

import {
  formatPercent,
  formatPrice,
  formatQuoteTime,
  formatVolume,
  movementClass,
  quoteIsDelayed,
  quoteName,
  QuoteRecord,
  useMarketData,
} from "@/components/market-data";
import { MarketStatusRow, MarketTape } from "@/components/market-tape";

function Unavailable() {
  return <span className="value-unavailable">Unavailable</span>;
}

function WatchlistSkeleton() {
  return (
    <div className="quote-list quote-list-loading" aria-label="Loading watchlist">
      {Array.from({ length: 5 }, (_, index) => (
        <div className="watchlist-row skeleton-row" key={index}>
          <span className="skeleton-line skeleton-name" />
          <span className="skeleton-line skeleton-value" />
          <span className="skeleton-line skeleton-value" />
          <span className="skeleton-line skeleton-value" />
        </div>
      ))}
    </div>
  );
}

function WatchlistRow({
  quote,
  marketOpen,
  nowMs,
}: {
  quote: QuoteRecord;
  marketOpen: boolean;
  nowMs: number;
}) {
  const price = formatPrice(quote.last);
  const percent = formatPercent(quote.changePct);
  const volume = formatVolume(quote.volume);
  const quoteTime = formatQuoteTime(quote.asOf);
  const delayed = quoteIsDelayed(quote, marketOpen, nowMs);

  return (
    <div className="watchlist-row">
      <div className="watchlist-company">
        <Link href={`/stock/${encodeURIComponent(quote.symbol)}`}>
          {quote.symbol}
        </Link>
        <span>{quoteName(quote.symbol)}</span>
      </div>
      <div className="quote-cell">
        <span className="mobile-cell-label">Last</span>
        {price ?? <Unavailable />}
      </div>
      <div className={`quote-cell ${movementClass(quote.changePct)}`}>
        <span className="mobile-cell-label">Today</span>
        {percent ?? <Unavailable />}
      </div>
      <div className="quote-cell">
        <span className="mobile-cell-label">Volume</span>
        {volume ?? <Unavailable />}
      </div>
      <div className="quote-cell quote-time-cell">
        <span className="mobile-cell-label">Quote time</span>
        {quoteTime === null ? (
          <Unavailable />
        ) : (
          <time dateTime={quote.asOf ?? undefined}>{quoteTime}</time>
        )}
        {delayed ? <span className="delayed-badge">Delayed</span> : null}
      </div>
    </div>
  );
}

export function DashboardQuotes() {
  const market = useMarketData();
  const quotes = market.data?.quotes ?? [];
  const indices = market.data?.indices ?? [];

  return (
    <div className="market-workspace">
      <MarketTape
        data={market.data}
        error={market.error}
        isLoading={market.isLoading}
        nowMs={market.nowMs}
      />
      <MarketStatusRow market={market} />

      <div className="dashboard-market-grid">
        <section className="market-card watchlist-card">
          <div className="card-heading">
            <div>
              <p className="section-kicker">Your watchlist</p>
              <h2>Companies you&apos;re tracking</h2>
            </div>
            {!market.isLoading && quotes.length > 0 ? (
              <span className="card-count">
                {quotes.length} {quotes.length === 1 ? "symbol" : "symbols"}
              </span>
            ) : null}
          </div>

          {!market.isLoading && quotes.length > 0 ? (
            <div className="watchlist-row watchlist-header" aria-hidden="true">
              <span>Company</span>
              <span>Last</span>
              <span>Today</span>
              <span>Volume</span>
              <span>Quote time</span>
            </div>
          ) : null}

          {market.isLoading ? <WatchlistSkeleton /> : null}
          {!market.isLoading && quotes.length === 0 ? (
            <div className="market-empty-state">
              <span className="empty-state-mark" aria-hidden="true">
                D
              </span>
              <div>
                <h3>No watchlist quotes yet</h3>
                <p>
                  Your tracked symbols will appear here when validated market
                  data is available.
                </p>
              </div>
            </div>
          ) : null}
          {!market.isLoading && quotes.length > 0 ? (
            <div className="quote-list">
              {quotes.map((quote) => (
                <WatchlistRow
                  key={quote.symbol}
                  quote={quote}
                  marketOpen={market.data?.marketOpen ?? false}
                  nowMs={market.nowMs}
                />
              ))}
            </div>
          ) : null}
        </section>

        <aside className="dashboard-side-stack">
          <section className="market-card glance-card">
            <div className="card-heading compact-heading">
              <div>
                <p className="section-kicker">At a glance</p>
                <h2>Broad market</h2>
              </div>
            </div>
            {market.isLoading ? (
              <div className="glance-list" aria-label="Loading market indices">
                {Array.from({ length: 3 }, (_, index) => (
                  <div className="glance-row" key={index}>
                    <span className="skeleton-line skeleton-symbol" />
                    <span className="skeleton-line skeleton-value" />
                  </div>
                ))}
              </div>
            ) : indices.length === 0 ? (
              <p className="inline-empty">
                Broad-market quotes are unavailable right now.
              </p>
            ) : (
              <div className="glance-list">
                {indices.map((quote) => {
                  const price = formatPrice(quote.last);
                  const percent = formatPercent(quote.changePct);
                  return (
                    <div className="glance-row" key={quote.symbol}>
                      <div>
                        <strong>{quote.symbol}</strong>
                        <span>Index proxy</span>
                      </div>
                      <div>
                        {price ?? <Unavailable />}
                        {percent === null ? null : (
                          <span className={movementClass(quote.changePct)}>
                            {percent}
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          <section className="market-card quick-ask-card">
            <p className="section-kicker">Quick ask</p>
            <h2>Put today&apos;s moves in context.</h2>
            <p>
              Ask Daybook to explain the factors behind a move without turning
              the answer into trading advice.
            </p>
            <Link className="button button-dark" href="/ask">
              Ask about a stock
            </Link>
          </section>
        </aside>
      </div>
    </div>
  );
}
