"use client";

import {
  formatPercent,
  formatPrice,
  MarketDataResult,
  movementClass,
  payloadIsDelayed,
  QuoteRecord,
  quoteIsDelayed,
} from "@/components/market-data";

type MarketTapeProps = Pick<
  MarketDataResult,
  "data" | "error" | "isLoading" | "nowMs"
>;

function TapeQuote({
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
  const delayed = quoteIsDelayed(quote, marketOpen, nowMs);

  return (
    <div className="tape-quote">
      <span className="tape-symbol">{quote.symbol}</span>
      {price === null ? (
        <span className="tape-unavailable">Unavailable</span>
      ) : (
        <span className="tape-price">{price}</span>
      )}
      {percent === null ? null : (
        <span className={`tape-change ${movementClass(quote.changePct)}`}>
          {percent}
        </span>
      )}
      {delayed ? <span className="delayed-badge">Delayed</span> : null}
    </div>
  );
}

export function MarketTape({
  data,
  error,
  isLoading,
  nowMs,
}: MarketTapeProps) {
  const quotes = data ? [...data.indices, ...data.quotes] : [];
  const delayed = data ? payloadIsDelayed(data, nowMs) : false;

  return (
    <section className="market-tape" aria-label="Live market tape">
      <div className="tape-heading">
        <div>
          <span
            className={`market-dot ${
              data?.marketOpen ? "market-dot-open" : "market-dot-closed"
            }`}
            aria-hidden="true"
          />
          <span className="tape-label">
            {data === null
              ? "Market tape"
              : data.marketOpen
                ? "Market open"
                : "Market closed"}
          </span>
        </div>
        <div className="tape-badges">
          {delayed ? <span className="delayed-badge">Delayed</span> : null}
          <span
            className="market-feed-badge"
            title="IEX prices are indicative and do not represent the full consolidated market."
            tabIndex={0}
          >
            Indicative (IEX)
          </span>
        </div>
      </div>

      <div className="tape-track">
        {isLoading
          ? Array.from({ length: 8 }, (_, index) => (
              <div className="tape-quote tape-skeleton" key={index}>
                <span className="skeleton-line skeleton-symbol" />
                <span className="skeleton-line skeleton-price" />
              </div>
            ))
          : quotes.map((quote) => (
              <TapeQuote
                key={`${quote.symbol}-${quote.asOf ?? "unavailable"}`}
                quote={quote}
                marketOpen={data?.marketOpen ?? false}
                nowMs={nowMs}
              />
            ))}
        {!isLoading && quotes.length === 0 ? (
          <div className="tape-empty">
            {error
              ? "Live prices are unavailable."
              : "No market symbols are available yet."}
          </div>
        ) : null}
      </div>
    </section>
  );
}

export function MarketStatusRow({
  market,
}: {
  market: MarketDataResult;
}) {
  const asOf = formatTimestamp(market.data?.asOf ?? null);
  const delayed = market.data
    ? payloadIsDelayed(market.data, market.nowMs)
    : false;

  return (
    <>
      {market.error ? (
        <div className="market-error-row" role="alert">
          <div>
            <strong>Quote update failed.</strong>
            <span>
              {market.error}
              {market.data
                ? " Showing the most recent validated values."
                : " No price values are being estimated."}
            </span>
          </div>
          <button
            className="retry-button"
            type="button"
            onClick={market.retry}
            disabled={market.isRefreshing}
          >
            {market.isRefreshing ? "Retrying…" : "Retry"}
          </button>
        </div>
      ) : null}

      <div className="market-meta" aria-live="polite">
        <span>
          {asOf === null ? (
            "As of unavailable"
          ) : (
            <>
              As of <time dateTime={market.data?.asOf ?? undefined}>{asOf}</time>
            </>
          )}
        </span>
        <span aria-hidden="true">·</span>
        <span>
          {market.data === null
            ? "Refresh cadence unavailable"
            : market.data.marketOpen
              ? "Refreshing every 15 seconds"
              : "Refreshing every 60 seconds off-hours"}
        </span>
        {market.isRefreshing ? (
          <>
            <span aria-hidden="true">·</span>
            <span>Updating…</span>
          </>
        ) : null}
        {delayed ? (
          <>
            <span aria-hidden="true">·</span>
            <span className="delayed-badge">Delayed</span>
          </>
        ) : null}
      </div>
    </>
  );
}

function formatTimestamp(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) {
    return null;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  }).format(timestamp);
}
