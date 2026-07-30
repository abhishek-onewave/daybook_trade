"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const MARKET_POLL_MS = 15_000;
const OFF_HOURS_POLL_MS = 60_000;
const STALE_AFTER_MS = 120_000;

const WATCHLIST_ORDER = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD"];
const INDEX_ORDER = ["SPY", "QQQ", "DIA"];

export type QuoteRecord = {
  symbol: string;
  last: number | null;
  changeAbs: number | null;
  changePct: number | null;
  volume: number | null;
  asOf: string | null;
};

export type MarketPayload = {
  asOf: string | null;
  feed: string;
  marketOpen: boolean;
  quotes: QuoteRecord[];
  indices: QuoteRecord[];
  refreshError: string | null;
  missingSymbols: string[];
};

type MarketState = {
  data: MarketPayload | null;
  error: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  nowMs: number;
};

export type MarketDataResult = MarketState & {
  retry: () => void;
  pollIntervalMs: number;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function finiteNumber(value: unknown, allowNegative = true): number | null {
  if (
    typeof value !== "number" &&
    (typeof value !== "string" || value.trim() === "")
  ) {
    return null;
  }

  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed) || (!allowNegative && parsed < 0)) {
    return null;
  }

  return parsed;
}

function validTimestamp(value: unknown): string | null {
  if (
    typeof value !== "string" ||
    value.trim() === "" ||
    !Number.isFinite(Date.parse(value))
  ) {
    return null;
  }

  return value;
}

function validSymbol(value: string): boolean {
  return /^[A-Z][A-Z0-9.-]{0,9}$/.test(value);
}

function parseQuote(symbol: string, value: unknown): QuoteRecord {
  const record = isRecord(value) ? value : {};

  return {
    symbol,
    last: finiteNumber(record.last, false),
    changeAbs: finiteNumber(record.change_abs),
    changePct: finiteNumber(record.change_pct),
    volume: finiteNumber(record.volume, false),
    asOf: validTimestamp(record.as_of),
  };
}

function symbolRank(symbol: string, order: string[]): number {
  const rank = order.indexOf(symbol);
  return rank === -1 ? order.length : rank;
}

function parseQuoteMap(value: unknown, order: string[]): QuoteRecord[] {
  if (!isRecord(value)) {
    throw new Error("The quote response did not contain a symbol map.");
  }

  const parsed = Object.entries(value)
    .map(([rawSymbol, quote]) => [rawSymbol.trim().toUpperCase(), quote] as const)
    .filter(([symbol]) => validSymbol(symbol))
    .map(([symbol, quote]) => parseQuote(symbol, quote))
  const bySymbol = new Map(parsed.map((quote) => [quote.symbol, quote]));
  const expected = order.map(
    (symbol) => bySymbol.get(symbol) ?? parseQuote(symbol, null),
  );
  const extras = parsed
    .filter((quote) => !order.includes(quote.symbol))
    .sort((left, right) => {
      const rankDifference =
        symbolRank(left.symbol, order) - symbolRank(right.symbol, order);
      return rankDifference || left.symbol.localeCompare(right.symbol);
    });
  return [...expected, ...extras];
}

function parseMissingSymbols(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((symbol): symbol is string => typeof symbol === "string")
    .map((symbol) => symbol.trim().toUpperCase())
    .filter(validSymbol);
}

function parseMarketPayload(value: unknown): MarketPayload {
  if (!isRecord(value)) {
    throw new Error("The quote service returned an invalid response.");
  }
  if (typeof value.market_open !== "boolean") {
    throw new Error("The quote response did not include market status.");
  }
  if (typeof value.feed !== "string" || value.feed.trim() === "") {
    throw new Error("The quote response did not identify its data feed.");
  }

  return {
    asOf: validTimestamp(value.as_of),
    feed: value.feed.trim(),
    marketOpen: value.market_open,
    quotes: parseQuoteMap(value.quotes, WATCHLIST_ORDER),
    indices: parseQuoteMap(value.indices, INDEX_ORDER),
    refreshError:
      typeof value.refresh_error === "string" &&
      value.refresh_error.trim() !== ""
        ? value.refresh_error.trim()
        : null,
    missingSymbols: parseMissingSymbols(value.missing_symbols),
  };
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.startsWith("The quote")) {
    return error.message;
  }
  return "Live quotes are temporarily unavailable.";
}

export function useMarketData(): MarketDataResult {
  const abortRef = useRef<AbortController | null>(null);
  const [state, setState] = useState<MarketState>({
    data: null,
    error: null,
    isLoading: true,
    isRefreshing: false,
    nowMs: 0,
  });

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState((previous) => ({
      ...previous,
      error: null,
      isLoading: previous.data === null,
      isRefreshing: previous.data !== null,
    }));

    try {
      const response = await fetch("/api/prices", {
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`Quote service returned HTTP ${response.status}.`);
      }

      const payload = parseMarketPayload(await response.json());
      if (controller.signal.aborted) {
        return;
      }

      setState({
        data: payload,
        error:
          payload.refreshError ??
          (payload.missingSymbols.length > 0
            ? `Validated quotes are unavailable for ${payload.missingSymbols.join(", ")}.`
            : null),
        isLoading: false,
        isRefreshing: false,
        nowMs: Date.now(),
      });
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      setState((previous) => ({
        ...previous,
        error: errorMessage(error),
        isLoading: false,
        isRefreshing: false,
        nowMs: Date.now(),
      }));
    }
  }, []);

  useEffect(() => {
    void load();

    return () => {
      abortRef.current?.abort();
    };
  }, [load]);

  const pollIntervalMs =
    state.data === null || state.data.marketOpen
      ? MARKET_POLL_MS
      : OFF_HOURS_POLL_MS;

  useEffect(() => {
    const interval = window.setInterval(() => {
      void load();
    }, pollIntervalMs);

    return () => {
      window.clearInterval(interval);
    };
  }, [load, pollIntervalMs]);

  return {
    ...state,
    retry: () => {
      void load();
    },
    pollIntervalMs,
  };
}

export function quoteIsDelayed(
  quote: QuoteRecord,
  marketOpen: boolean,
  nowMs: number,
): boolean {
  if (!marketOpen || quote.asOf === null || nowMs === 0) {
    return false;
  }
  return nowMs - Date.parse(quote.asOf) > STALE_AFTER_MS;
}

export function payloadIsDelayed(
  data: MarketPayload,
  nowMs: number,
): boolean {
  if (!data.marketOpen || nowMs === 0) {
    return false;
  }

  const payloadTime = data.asOf === null ? null : Date.parse(data.asOf);
  if (payloadTime !== null && nowMs - payloadTime > STALE_AFTER_MS) {
    return true;
  }

  return [...data.indices, ...data.quotes].some((quote) =>
    quoteIsDelayed(quote, data.marketOpen, nowMs),
  );
}

export function movementClass(value: number | null): string {
  if (value === null || value === 0) {
    return "market-flat";
  }
  return value > 0 ? "market-up" : "market-down";
}

export function formatPrice(value: number | null): string | null {
  if (value === null || !Number.isFinite(value)) {
    return null;
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatChange(value: number | null): string | null {
  const formatted = formatPrice(value === null ? null : Math.abs(value));
  if (formatted === null || value === null) {
    return null;
  }
  if (value === 0) {
    return formatted;
  }
  return `${value > 0 ? "+" : "−"}${formatted}`;
}

export function formatPercent(value: number | null): string | null {
  if (value === null || !Number.isFinite(value)) {
    return null;
  }
  if (value === 0) {
    return "0.00%";
  }
  return `${value > 0 ? "+" : "−"}${Math.abs(value).toFixed(2)}%`;
}

export function formatVolume(value: number | null): string | null {
  if (value === null || !Number.isFinite(value)) {
    return null;
  }
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatTimestamp(value: string | null): string | null {
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

export function formatQuoteTime(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) {
    return null;
  }

  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
  }).format(timestamp);
}

export function quoteName(symbol: string): string {
  const names: Record<string, string> = {
    AAPL: "Apple",
    AMD: "Advanced Micro Devices",
    MSFT: "Microsoft",
    NVDA: "NVIDIA",
    TSLA: "Tesla",
  };
  return names[symbol] ?? symbol;
}
