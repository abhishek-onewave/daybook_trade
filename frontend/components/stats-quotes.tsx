"use client";

import Link from "next/link";

import {
  formatChange,
  formatPercent,
  formatPrice,
  formatQuoteTime,
  formatVolume,
  movementClass,
  quoteIsDelayed,
  QuoteRecord,
  useMarketData,
} from "@/components/market-data";
import { MarketStatusRow, MarketTape } from "@/components/market-tape";

const EXPECTED_INDICES = ["SPY", "QQQ", "DIA"];

function Unavailable() {
  return <span className="value-unavailable">Unavailable</span>;
}

function IndexTile({
  symbol,
  quote,
  loading,
  marketOpen,
  nowMs,
}: {
  symbol: string;
  quote: QuoteRecord | undefined;
  loading: boolean;
  marketOpen: boolean;
  nowMs: number;
}) {
  if (loading) {
    return (
      <div className="index-tile index-tile-loading">
        <span className="skeleton-line skeleton-symbol" />
        <span className="skeleton-line skeleton-index-price" />
        <span className="skeleton-line skeleton-value" />
      </div>
    );
  }

  const price = formatPrice(quote?.last ?? null);
  const change = formatChange(quote?.changeAbs ?? null);
  const percent = formatPercent(quote?.changePct ?? null);
  const quoteTime = formatQuoteTime(quote?.asOf ?? null);
  const delayed = quote
    ? quoteIsDelayed(quote, marketOpen, nowMs)
    : false;

  return (
    <article className="index-tile">
      <div className="index-tile-heading">
        <div>
          <span className="index-symbol">{symbol}</span>
          <span>Index proxy</span>
        </div>
        {delayed ? <span className="delayed-badge">Delayed</span> : null}
      </div>
      <div className="index-price">{price ?? <Unavailable />}</div>
      <div className={`index-change ${movementClass(quote?.changePct ?? null)}`}>
        {change === null || percent === null ? (
          <Unavailable />
        ) : (
          `${change} (${percent})`
        )}
      </div>
      <div className="index-time">
        {quoteTime === null ? (
          "Quote time unavailable"
        ) : (
          <>
            Quote <time dateTime={quote?.asOf ?? undefined}>{quoteTime}</time>
          </>
        )}
      </div>
    </article>
  );
}

function StatsTableSkeleton() {
  return (
    <tbody aria-label="Loading watchlist statistics">
      {Array.from({ length: 5 }, (_, index) => (
        <tr key={index}>
          {Array.from({ length: 6 }, (_, cellIndex) => (
            <td key={cellIndex}>
              <span className="skeleton-line skeleton-table-cell" />
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

function QuoteRow({
  quote,
  marketOpen,
  nowMs,
}: {
  quote: QuoteRecord;
  marketOpen: boolean;
  nowMs: number;
}) {
  const price = formatPrice(quote.last);
  const change = formatChange(quote.changeAbs);
  const percent = formatPercent(quote.changePct);
  const volume = formatVolume(quote.volume);
  const quoteTime = formatQuoteTime(quote.asOf);
  const delayed = quoteIsDelayed(quote, marketOpen, nowMs);

  return (
    <tr>
      <th scope="row">
        <Link href={`/stock/${encodeURIComponent(quote.symbol)}`}>
          {quote.symbol}
        </Link>
      </th>
      <td>{price ?? <Unavailable />}</td>
      <td className={movementClass(quote.changeAbs)}>
        {change ?? <Unavailable />}
      </td>
      <td className={movementClass(quote.changePct)}>
        {percent ?? <Unavailable />}
      </td>
      <td>{volume ?? <Unavailable />}</td>
      <td>
        <span className="table-quote-time">
          {quoteTime === null ? (
            <Unavailable />
          ) : (
            <time dateTime={quote.asOf ?? undefined}>{quoteTime}</time>
          )}
          {delayed ? <span className="delayed-badge">Delayed</span> : null}
        </span>
      </td>
    </tr>
  );
}

export function StatsQuotes() {
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

      <section className="stats-section" aria-labelledby="index-heading">
        <div className="section-heading-row">
          <div>
            <p className="section-kicker">Broad market</p>
            <h2 id="index-heading">Index proxies</h2>
          </div>
          <p>
            SPY, QQQ, and DIA provide an indicative view of major U.S. equity
            benchmarks.
          </p>
        </div>

        <div className="index-grid">
          {EXPECTED_INDICES.map((symbol) => (
            <IndexTile
              key={symbol}
              symbol={symbol}
              quote={indices.find((quote) => quote.symbol === symbol)}
              loading={market.isLoading}
              marketOpen={market.data?.marketOpen ?? false}
              nowMs={market.nowMs}
            />
          ))}
        </div>
      </section>

      <section
        className="market-card stats-table-card"
        aria-labelledby="watchlist-stats-heading"
      >
        <div className="card-heading stats-card-heading">
          <div>
            <p className="section-kicker">Your watchlist</p>
            <h2 id="watchlist-stats-heading">Live statistics</h2>
          </div>
          <span className="cadence-label">
            {market.data === null
              ? "Cadence unavailable"
              : market.data.marketOpen
                ? "15-second cadence"
                : "60-second off-hours cadence"}
          </span>
        </div>

        <div className="stats-table-scroll">
          <table className="stats-table">
            <thead>
              <tr>
                <th scope="col">Symbol</th>
                <th scope="col">Last</th>
                <th scope="col">Change</th>
                <th scope="col">Change %</th>
                <th scope="col">Volume</th>
                <th scope="col">Quote time</th>
              </tr>
            </thead>
            {market.isLoading ? <StatsTableSkeleton /> : null}
            {!market.isLoading && quotes.length > 0 ? (
              <tbody>
                {quotes.map((quote) => (
                  <QuoteRow
                    key={quote.symbol}
                    quote={quote}
                    marketOpen={market.data?.marketOpen ?? false}
                    nowMs={market.nowMs}
                  />
                ))}
              </tbody>
            ) : null}
          </table>
        </div>

        {!market.isLoading && quotes.length === 0 ? (
          <div className="market-empty-state stats-empty-state">
            <span className="empty-state-mark" aria-hidden="true">
              D
            </span>
            <div>
              <h3>No watchlist statistics available</h3>
              <p>
                Validated quote rows will appear here when the price service has
                watchlist data.
              </p>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
