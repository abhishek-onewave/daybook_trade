"""Live IEX quote and historical bar routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..services.alpaca import (
    ALPACA_FEED,
    BAR_RANGES,
    INDEX_SYMBOLS,
    MARKET_POLL_SECONDS,
    OFF_HOURS_POLL_SECONDS,
    PRICE_SYMBOLS,
    WATCHLIST_SYMBOLS,
    AlpacaClient,
    MarketBar,
    MarketQuote,
    is_us_market_open,
    load_quote_cache,
    normalize_symbol,
    upsert_quote_cache,
)

router = APIRouter(prefix="/api", tags=["prices"])

PriceStatus = Literal["live", "delayed", "stale", "partial"]
SupportedRange = Literal["1D", "1W", "1M", "6M", "1Y"]


class QuoteResponse(BaseModel):
    last: float
    change_abs: float
    change_pct: float
    volume: int
    as_of: datetime


class PricesResponse(BaseModel):
    as_of: datetime
    quotes: dict[str, QuoteResponse]
    indices: dict[str, QuoteResponse]
    feed: Literal["iex"]
    status: PriceStatus
    market_open: bool
    delayed: bool
    source_label: str
    missing_symbols: list[str]
    refresh_error: str | None = None


class BarResponse(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class BarsResponse(BaseModel):
    symbol: str
    range: SupportedRange
    as_of: datetime
    feed: Literal["iex"]
    bars: list[BarResponse]


class ErrorDetail(BaseModel):
    code: str
    message: str


class MarketDataUnavailableResponse(BaseModel):
    as_of: datetime
    feed: Literal["iex"]
    status: Literal["unavailable"]
    market_open: bool
    quotes: dict[str, QuoteResponse] | None = None
    indices: dict[str, QuoteResponse] | None = None
    error: ErrorDetail


def _quote_response(quote: MarketQuote) -> QuoteResponse:
    return QuoteResponse(
        last=quote.last,
        change_abs=quote.change_abs,
        change_pct=quote.change_pct,
        volume=quote.volume,
        as_of=quote.as_of,
    )


def _bar_response(bar: MarketBar) -> BarResponse:
    return BarResponse(
        time=bar.time,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
    )


def _unavailable_response(
    *,
    code: str,
    message: str,
    market_open: bool,
    include_price_maps: bool,
) -> JSONResponse:
    payload = MarketDataUnavailableResponse(
        as_of=datetime.now(UTC),
        feed=ALPACA_FEED,
        status="unavailable",
        market_open=market_open,
        quotes={} if include_price_maps else None,
        indices={} if include_price_maps else None,
        error=ErrorDetail(code=code, message=message),
    )
    content = payload.model_dump(mode="json", exclude_none=True)
    return JSONResponse(status_code=503, content=content)


def _refresh_age(quotes: dict[str, MarketQuote], now: datetime) -> timedelta | None:
    if not quotes:
        return None
    oldest = min(quote.as_of for quote in quotes.values())
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=UTC)
    return max(now - oldest.astimezone(UTC), timedelta())


def _needs_refresh(
    quotes: dict[str, MarketQuote],
    *,
    now: datetime,
    market_open: bool,
) -> bool:
    if any(symbol not in quotes for symbol in PRICE_SYMBOLS):
        return True
    age = _refresh_age(quotes, now)
    refresh_seconds = MARKET_POLL_SECONDS if market_open else OFF_HOURS_POLL_SECONDS
    return age is None or age.total_seconds() >= refresh_seconds


async def _refresh_prices(
    request: Request,
    settings: Settings,
    session: Session,
    *,
    now: datetime,
    market_open: bool,
) -> dict[str, MarketQuote]:
    owned_client: AlpacaClient | None = None
    client = getattr(request.app.state, "alpaca_client", None)
    if client is None:
        owned_client = AlpacaClient(settings)
        client = owned_client

    lock = getattr(request.app.state, "quote_refresh_lock", None)
    try:
        if lock is None:
            fetched = await client.fetch_snapshots(PRICE_SYMBOLS)
            if fetched:
                upsert_quote_cache(session, fetched)
        else:
            async with lock:
                session.expire_all()
                current = load_quote_cache(session)
                if not _needs_refresh(current, now=now, market_open=market_open):
                    return current
                fetched = await client.fetch_snapshots(PRICE_SYMBOLS)
                if fetched:
                    upsert_quote_cache(session, fetched)
        session.expire_all()
        return load_quote_cache(session)
    finally:
        if owned_client is not None:
            await owned_client.aclose()


@router.get(
    "/prices",
    response_model=PricesResponse,
    responses={503: {"model": MarketDataUnavailableResponse}},
)
async def get_prices(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PricesResponse | JSONResponse:
    now = datetime.now(UTC)
    market_open = is_us_market_open(now)
    cached = load_quote_cache(session)
    refresh_error: str | None = None

    if settings.alpaca_enabled and _needs_refresh(
        cached,
        now=now,
        market_open=market_open,
    ):
        try:
            cached = await _refresh_prices(
                request,
                settings,
                session,
                now=now,
                market_open=market_open,
            )
        except Exception:
            refresh_error = "Latest Alpaca refresh failed; serving cached data."

    if not cached:
        message = (
            "Alpaca is configured but disabled while preview mode is active."
            if settings.alpaca_configured and settings.daybook_demo_mode
            else (
                "Alpaca market data is temporarily unavailable."
                if settings.alpaca_configured
                else "Alpaca credentials are not configured."
            )
        )
        return _unavailable_response(
            code="MARKET_DATA_UNAVAILABLE",
            message=message,
            market_open=market_open,
            include_price_maps=True,
        )

    missing_symbols = [symbol for symbol in PRICE_SYMBOLS if symbol not in cached]
    age = _refresh_age(cached, now) or timedelta()
    delayed = market_open and age > timedelta(minutes=2)
    refresh_after = timedelta(
        seconds=MARKET_POLL_SECONDS if market_open else OFF_HOURS_POLL_SECONDS
    )
    if missing_symbols:
        status: PriceStatus = "partial"
    elif delayed:
        status = "delayed"
    elif age >= refresh_after:
        status = "stale"
    else:
        status = "live"

    quotes = {
        symbol: _quote_response(cached[symbol]) for symbol in WATCHLIST_SYMBOLS if symbol in cached
    }
    indices = {
        symbol: _quote_response(cached[symbol]) for symbol in INDEX_SYMBOLS if symbol in cached
    }
    return PricesResponse(
        as_of=max(quote.as_of for quote in cached.values()),
        quotes=quotes,
        indices=indices,
        feed=ALPACA_FEED,
        status=status,
        market_open=market_open,
        delayed=delayed,
        source_label="indicative (IEX)",
        missing_symbols=missing_symbols,
        refresh_error=refresh_error,
    )


@router.get(
    "/bars",
    response_model=BarsResponse,
    responses={503: {"model": MarketDataUnavailableResponse}},
)
async def get_bars(
    request: Request,
    symbol: str = Query(min_length=1, max_length=16),
    range_name: SupportedRange = Query(alias="range"),
    settings: Settings = Depends(get_settings),
) -> BarsResponse | JSONResponse:
    try:
        normalized = normalize_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    if range_name not in BAR_RANGES:
        raise HTTPException(status_code=422, detail="Unsupported range.")
    market_open = is_us_market_open()
    if not settings.alpaca_configured:
        return _unavailable_response(
            code="MARKET_DATA_NOT_CONFIGURED",
            message="Alpaca credentials are not configured.",
            market_open=market_open,
            include_price_maps=False,
        )

    owned_client: AlpacaClient | None = None
    client = getattr(request.app.state, "alpaca_client", None)
    if client is None:
        owned_client = AlpacaClient(settings)
        client = owned_client
    try:
        bars = await client.fetch_bars(normalized, range_name)
    except Exception:
        return _unavailable_response(
            code="MARKET_DATA_UNAVAILABLE",
            message="Historical market data is temporarily unavailable.",
            market_open=market_open,
            include_price_maps=False,
        )
    finally:
        if owned_client is not None:
            await owned_client.aclose()

    if not bars:
        return _unavailable_response(
            code="NO_BAR_DATA",
            message=f"No historical market data is available for {normalized}.",
            market_open=market_open,
            include_price_maps=False,
        )
    return BarsResponse(
        symbol=normalized,
        range=range_name,
        as_of=datetime.now(UTC),
        feed=ALPACA_FEED,
        bars=[_bar_response(bar) for bar in bars],
    )
