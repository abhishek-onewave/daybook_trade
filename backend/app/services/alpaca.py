"""Alpaca REST market-data client, parsing, caching, and quote polling."""

from __future__ import annotations

import asyncio
import logging
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any, Final
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.db import SessionLocal
from backend.app.models import QuoteCache

logger = logging.getLogger(__name__)

ALPACA_DATA_BASE_URL: Final = "https://data.alpaca.markets"
ALPACA_FEED: Final = "iex"
WATCHLIST_SYMBOLS: Final = ("NVDA", "AAPL", "MSFT", "TSLA", "AMD")
INDEX_SYMBOLS: Final = ("SPY", "QQQ", "DIA")
PRICE_SYMBOLS: Final = WATCHLIST_SYMBOLS + INDEX_SYMBOLS
MARKET_POLL_SECONDS: Final = 15
OFF_HOURS_POLL_SECONDS: Final = 60

_EASTERN = ZoneInfo("America/New_York")
_SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,15}$")


class AlpacaError(RuntimeError):
    """A safe-to-surface category for Alpaca request or payload failures."""


class AlpacaNotConfiguredError(AlpacaError):
    """Raised when a market-data request is attempted without credentials."""


class AlpacaAPIError(AlpacaError):
    """Raised when Alpaca rejects a request or returns an invalid response."""


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: str
    last: float
    change_abs: float
    change_pct: float
    volume: int
    as_of: datetime


@dataclass(frozen=True, slots=True)
class MarketBar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class BarRange:
    timeframe: str
    lookback: timedelta
    limit: int = 1_000


BAR_RANGES: Final[dict[str, BarRange]] = {
    "1D": BarRange(timeframe="5Min", lookback=timedelta(days=3)),
    "1W": BarRange(timeframe="30Min", lookback=timedelta(days=10)),
    # Hourly bars provide roughly 150 regular-session points for a calendar month.
    "1M": BarRange(timeframe="1Hour", lookback=timedelta(days=45)),
    "6M": BarRange(timeframe="1Day", lookback=timedelta(days=220)),
    "1Y": BarRange(timeframe="1Day", lookback=timedelta(days=400)),
}


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not _SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError("Symbol must be a valid US equity ticker.")
    return normalized


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first(mapping: Mapping[str, Any], *keys: str) -> object:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _finite_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _nonnegative_int(value: object) -> int | None:
    number = _finite_float(value)
    if number is None or number < 0 or not number.is_integer():
        return None
    return int(number)


def _utc_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _bar_value(bar: Mapping[str, Any], short_key: str, long_key: str) -> object:
    return _first(bar, short_key, long_key)


def parse_snapshots(
    payload: Mapping[str, Any],
    symbols: Sequence[str] | None = None,
    *,
    fetched_at: datetime | None = None,
) -> dict[str, MarketQuote]:
    """Parse Alpaca's multi-snapshot response, omitting incomplete/invalid symbols."""

    cache_timestamp = fetched_at or datetime.now(UTC)
    if cache_timestamp.tzinfo is None:
        cache_timestamp = cache_timestamp.replace(tzinfo=UTC)
    cache_timestamp = cache_timestamp.astimezone(UTC)
    wrapped = payload.get("snapshots")
    snapshots = _as_mapping(wrapped) if isinstance(wrapped, Mapping) else payload
    if symbols is not None:
        requested = tuple(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
    else:
        normalized_payload_symbols: list[str] = []
        for raw_symbol in snapshots:
            try:
                normalized_payload_symbols.append(normalize_symbol(str(raw_symbol)))
            except ValueError:
                continue
        requested = tuple(dict.fromkeys(normalized_payload_symbols))
    quotes: dict[str, MarketQuote] = {}

    for symbol in requested:
        snapshot = _as_mapping(snapshots.get(symbol))
        if not snapshot:
            continue

        latest_trade = _as_mapping(_first(snapshot, "latestTrade", "latest_trade"))
        minute_bar = _as_mapping(_first(snapshot, "minuteBar", "minute_bar"))
        daily_bar = _as_mapping(_first(snapshot, "dailyBar", "daily_bar"))
        previous_daily_bar = _as_mapping(
            _first(snapshot, "prevDailyBar", "previousDailyBar", "prev_daily_bar")
        )

        price_sources = (
            _bar_value(latest_trade, "p", "price"),
            _bar_value(minute_bar, "c", "close"),
            _bar_value(daily_bar, "c", "close"),
        )
        last: float | None = None
        for raw_price in price_sources:
            candidate_price = _finite_float(raw_price)
            if candidate_price is not None and candidate_price >= 0:
                last = candidate_price
                break

        previous_close = _finite_float(_bar_value(previous_daily_bar, "c", "close"))
        volume = _nonnegative_int(_bar_value(daily_bar, "v", "volume"))
        if last is None or previous_close is None or previous_close <= 0 or volume is None:
            continue

        change_abs = last - previous_close
        change_pct = (change_abs / previous_close) * 100
        if not math.isfinite(change_abs) or not math.isfinite(change_pct):
            continue
        quotes[symbol] = MarketQuote(
            symbol=symbol,
            last=last,
            change_abs=change_abs,
            change_pct=change_pct,
            volume=volume,
            as_of=cache_timestamp,
        )

    return quotes


def parse_bars(payload: Mapping[str, Any], symbol: str) -> list[MarketBar]:
    """Parse one symbol from Alpaca's multi-symbol bars payload."""

    normalized = normalize_symbol(symbol)
    bars_container = payload.get("bars")
    if isinstance(bars_container, Mapping):
        raw_bars = bars_container.get(normalized)
    else:
        raw_bars = bars_container
    if not isinstance(raw_bars, list):
        return []

    parsed_by_time: dict[datetime, MarketBar] = {}
    for raw_bar in raw_bars:
        bar = _as_mapping(raw_bar)
        timestamp = _utc_datetime(_bar_value(bar, "t", "timestamp"))
        open_price = _finite_float(_bar_value(bar, "o", "open"))
        high = _finite_float(_bar_value(bar, "h", "high"))
        low = _finite_float(_bar_value(bar, "l", "low"))
        close = _finite_float(_bar_value(bar, "c", "close"))
        volume = _nonnegative_int(_bar_value(bar, "v", "volume"))
        prices = (open_price, high, low, close)
        if (
            timestamp is None
            or any(price is None or price < 0 for price in prices)
            or volume is None
        ):
            continue
        assert open_price is not None and high is not None and low is not None and close is not None
        if high < max(open_price, low, close) or low > min(open_price, high, close):
            continue
        parsed_by_time[timestamp] = MarketBar(
            time=timestamp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )
    return [parsed_by_time[timestamp] for timestamp in sorted(parsed_by_time)]


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class AlpacaClient:
    """Minimal async client for Alpaca's official stock market-data REST API."""

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not settings.alpaca_configured:
            raise AlpacaNotConfiguredError("Alpaca market data is not configured.")
        self._headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key_id,
            "APCA-API-SECRET-KEY": settings.alpaca_api_secret_key,
        }
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            base_url=ALPACA_DATA_BASE_URL,
            timeout=httpx.Timeout(10.0),
        )

    async def __aenter__(self) -> AlpacaClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def _get_json(self, path: str, params: Mapping[str, object]) -> Mapping[str, Any]:
        try:
            response = await self._http_client.get(
                f"{ALPACA_DATA_BASE_URL}{path}",
                params=params,
                headers=self._headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise AlpacaAPIError(
                f"Alpaca market-data request failed with status {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise AlpacaAPIError("Alpaca market-data request failed.") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise AlpacaAPIError("Alpaca returned invalid JSON.") from exc
        if not isinstance(payload, Mapping):
            raise AlpacaAPIError("Alpaca returned an unexpected payload.")
        return payload

    async def fetch_snapshots(self, symbols: Sequence[str]) -> dict[str, MarketQuote]:
        normalized = tuple(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
        if not normalized:
            return {}
        payload = await self._get_json(
            "/v2/stocks/snapshots",
            {"symbols": ",".join(normalized), "feed": ALPACA_FEED},
        )
        return parse_snapshots(payload, normalized, fetched_at=datetime.now(UTC))

    async def fetch_bars(
        self,
        symbol: str,
        range_name: str,
        *,
        now: datetime | None = None,
    ) -> list[MarketBar]:
        normalized = normalize_symbol(symbol)
        try:
            range_config = BAR_RANGES[range_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported range: {range_name}") from exc
        end = now or datetime.now(UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        end = end.astimezone(UTC)
        payload = await self._get_json(
            "/v2/stocks/bars",
            {
                "symbols": normalized,
                "timeframe": range_config.timeframe,
                "start": _rfc3339(end - range_config.lookback),
                "end": _rfc3339(end),
                "limit": range_config.limit,
                "adjustment": "raw",
                "feed": ALPACA_FEED,
                "sort": "asc",
            },
        )
        return parse_bars(payload, normalized)


def _storage_number(value: float) -> str:
    return format(value, ".15g")


def upsert_quote_cache(session: Session, quotes: Mapping[str, MarketQuote]) -> None:
    """Atomically insert or update parsed quotes in ``quotes_cache``."""

    try:
        if session.get_bind().dialect.name == "postgresql":
            values = [
                {
                    "symbol": normalize_symbol(symbol),
                    "last": _storage_number(quote.last),
                    "change_abs": _storage_number(quote.change_abs),
                    "change_pct": _storage_number(quote.change_pct),
                    "volume": quote.volume,
                    "as_of": quote.as_of,
                }
                for symbol, quote in quotes.items()
            ]
            if values:
                insert = postgresql_insert(QuoteCache).values(values)
                session.execute(
                    insert.on_conflict_do_update(
                        index_elements=[QuoteCache.symbol],
                        set_={
                            "last": insert.excluded.last,
                            "change_abs": insert.excluded.change_abs,
                            "change_pct": insert.excluded.change_pct,
                            "volume": insert.excluded.volume,
                            "as_of": insert.excluded.as_of,
                        },
                        where=insert.excluded.as_of >= QuoteCache.as_of,
                    )
                )
            session.commit()
            return

        for symbol, quote in quotes.items():
            normalized = normalize_symbol(symbol)
            row = session.get(QuoteCache, normalized)
            if row is None:
                row = QuoteCache(
                    symbol=normalized,
                    last=_storage_number(quote.last),
                    change_abs=_storage_number(quote.change_abs),
                    change_pct=_storage_number(quote.change_pct),
                    volume=quote.volume,
                    as_of=quote.as_of,
                )
                session.add(row)
            else:
                row.last = _storage_number(quote.last)
                row.change_abs = _storage_number(quote.change_abs)
                row.change_pct = _storage_number(quote.change_pct)
                row.volume = quote.volume
                row.as_of = quote.as_of
        session.commit()
    except Exception:
        session.rollback()
        raise


def load_quote_cache(
    session: Session,
    symbols: Sequence[str] = PRICE_SYMBOLS,
) -> dict[str, MarketQuote]:
    normalized = tuple(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
    if not normalized:
        return {}
    rows = session.scalars(select(QuoteCache).where(QuoteCache.symbol.in_(normalized))).all()
    quotes: dict[str, MarketQuote] = {}
    for row in rows:
        last = _finite_float(row.last)
        change_abs = _finite_float(row.change_abs)
        change_pct = _finite_float(row.change_pct)
        volume = _nonnegative_int(row.volume)
        as_of = _utc_datetime(row.as_of)
        if None in (last, change_abs, change_pct, volume, as_of):
            continue
        assert (
            last is not None
            and change_abs is not None
            and change_pct is not None
            and volume is not None
            and as_of is not None
        )
        quotes[row.symbol] = MarketQuote(
            symbol=row.symbol,
            last=last,
            change_abs=change_abs,
            change_pct=change_pct,
            volume=volume,
            as_of=as_of,
        )
    return quotes


async def refresh_quote_cache(
    client: AlpacaClient,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> dict[str, MarketQuote]:
    quotes = await client.fetch_snapshots(PRICE_SYMBOLS)
    if quotes:
        with session_factory() as session:
            upsert_quote_cache(session, quotes)
    return quotes


def is_us_market_open(at: datetime | None = None) -> bool:
    """Return whether ``at`` falls in regular US equity hours (weekdays, ET)."""

    moment = at or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    eastern = moment.astimezone(_EASTERN)
    local_time = eastern.time().replace(tzinfo=None)
    return eastern.weekday() < 5 and time(9, 30) <= local_time < time(16)


def quote_poll_interval(at: datetime | None = None) -> int:
    return MARKET_POLL_SECONDS if is_us_market_open(at) else OFF_HOURS_POLL_SECONDS


async def run_quote_poller(
    client: AlpacaClient,
    stop_event: asyncio.Event,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
    refresh_lock: asyncio.Lock | None = None,
) -> None:
    """Refresh immediately, then every 15s in-session and 60s off-hours."""

    while not stop_event.is_set():
        try:
            if refresh_lock is None:
                await refresh_quote_cache(client, session_factory=session_factory)
            else:
                async with refresh_lock:
                    await refresh_quote_cache(client, session_factory=session_factory)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # Do not log request objects, headers, or payloads: they can carry credentials.
            logger.warning("Alpaca quote refresh failed (%s).", type(exc).__name__)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=quote_poll_interval())
        except TimeoutError:
            continue
