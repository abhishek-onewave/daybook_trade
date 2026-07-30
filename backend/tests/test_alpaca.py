import asyncio
import math
from datetime import UTC, datetime, timedelta

import httpx
from backend.app.config import Settings
from backend.app.models import QuoteCache
from backend.app.services.alpaca import (
    ALPACA_DATA_BASE_URL,
    AlpacaClient,
    MarketQuote,
    is_us_market_open,
    load_quote_cache,
    parse_bars,
    parse_snapshots,
    quote_poll_interval,
    upsert_quote_cache,
)
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

FETCHED_AT = datetime(2026, 7, 29, 20, 0, tzinfo=UTC)


def _snapshot(
    *,
    latest: object = 125.5,
    minute_close: object = 124.0,
    daily_close: object = 123.0,
    previous_close: object = 100.0,
    volume: object = 1_234,
) -> dict[str, object]:
    return {
        "latestTrade": {"p": latest, "t": "2026-07-29T19:59:59Z"},
        "minuteBar": {"c": minute_close, "t": "2026-07-29T19:59:00Z"},
        "dailyBar": {"c": daily_close, "v": volume, "t": "2026-07-29T13:30:00Z"},
        "prevDailyBar": {"c": previous_close, "t": "2026-07-28T13:30:00Z"},
    }


def _bar_payload(count: int = 60) -> dict[str, object]:
    start = datetime(2026, 6, 1, 14, 0, tzinfo=UTC)
    bars = []
    for index in range(count):
        close = 100.0 + index
        bars.append(
            {
                "t": (start + timedelta(hours=index)).isoformat().replace("+00:00", "Z"),
                "o": close - 0.5,
                "h": close + 1.0,
                "l": close - 1.0,
                "c": close,
                "v": 10_000 + index,
            }
        )
    return {"bars": {"NVDA": bars}}


def test_snapshot_parser_prefers_trade_and_uses_fetch_time() -> None:
    payload = {
        "snapshots": {
            "NVDA": _snapshot(),
            "AAPL": _snapshot(latest="NaN", minute_close=95, previous_close=90, volume=500),
            "MSFT": _snapshot(previous_close=0),
        }
    }

    quotes = parse_snapshots(payload, ["NVDA", "AAPL", "MSFT"], fetched_at=FETCHED_AT)

    assert set(quotes) == {"NVDA", "AAPL"}
    assert quotes["NVDA"] == MarketQuote(
        symbol="NVDA",
        last=125.5,
        change_abs=25.5,
        change_pct=25.5,
        volume=1_234,
        as_of=FETCHED_AT,
    )
    assert quotes["AAPL"].last == 95
    assert math.isclose(quotes["AAPL"].change_pct, 5.555555555555555)
    assert quotes["AAPL"].as_of == FETCHED_AT


def test_bars_parser_sorts_deduplicates_and_drops_non_finite_values() -> None:
    payload = _bar_payload(3)
    raw_bars = payload["bars"]["NVDA"]  # type: ignore[index]
    assert isinstance(raw_bars, list)
    raw_bars.reverse()
    raw_bars.append(
        {
            "t": "2026-06-01T20:00:00Z",
            "o": "NaN",
            "h": 102,
            "l": 99,
            "c": 101,
            "v": 100,
        }
    )

    bars = parse_bars(payload, "nvda")

    assert len(bars) == 3
    assert bars == sorted(bars, key=lambda bar: bar.time)
    assert all(math.isfinite(bar.close) for bar in bars)


def test_client_uses_official_snapshot_endpoint_and_iex_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/snapshots"
        assert request.url.params["symbols"] == "NVDA,AAPL"
        assert request.url.params["feed"] == "iex"
        assert request.headers["APCA-API-KEY-ID"] == "test-key"
        assert request.headers["APCA-API-SECRET-KEY"] == "test-secret"
        return httpx.Response(200, json={"NVDA": _snapshot(), "AAPL": _snapshot()})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport,
            base_url=ALPACA_DATA_BASE_URL,
        ) as http_client:
            client = AlpacaClient(
                Settings(
                    _env_file=None,
                    alpaca_api_key_id="test-key",
                    alpaca_api_secret_key="test-secret",
                ),
                http_client=http_client,
            )
            quotes = await client.fetch_snapshots(["nvda", "AAPL", "NVDA"])
        assert set(quotes) == {"NVDA", "AAPL"}

    asyncio.run(run())


def test_client_maps_one_month_to_hourly_official_bars_request() -> None:
    now = datetime(2026, 7, 29, 20, 0, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/stocks/bars"
        assert request.url.params["symbols"] == "NVDA"
        assert request.url.params["timeframe"] == "1Hour"
        assert request.url.params["start"] == "2026-06-14T20:00:00Z"
        assert request.url.params["end"] == "2026-07-29T20:00:00Z"
        assert request.url.params["limit"] == "1000"
        assert request.url.params["adjustment"] == "raw"
        assert request.url.params["feed"] == "iex"
        return httpx.Response(200, json=_bar_payload())

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport,
            base_url=ALPACA_DATA_BASE_URL,
        ) as http_client:
            client = AlpacaClient(
                Settings(
                    _env_file=None,
                    alpaca_api_key_id="test-key",
                    alpaca_api_secret_key="test-secret",
                ),
                http_client=http_client,
            )
            bars = await client.fetch_bars("NVDA", "1M", now=now)
        assert len(bars) == 60

    asyncio.run(run())


def test_quote_cache_upsert_replaces_rows_and_normalizes_sqlite_datetimes() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    QuoteCache.__table__.create(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        upsert_quote_cache(
            session,
            {
                "NVDA": MarketQuote(
                    symbol="NVDA",
                    last=100,
                    change_abs=1,
                    change_pct=1,
                    volume=10,
                    as_of=FETCHED_AT,
                )
            },
        )
        upsert_quote_cache(
            session,
            {
                "NVDA": MarketQuote(
                    symbol="NVDA",
                    last=101.25,
                    change_abs=2.25,
                    change_pct=2.2727272727,
                    volume=20,
                    as_of=FETCHED_AT + timedelta(seconds=15),
                )
            },
        )
        count = session.scalar(select(func.count()).select_from(QuoteCache))
        cached = load_quote_cache(session, ["NVDA"])

    assert count == 1
    assert cached["NVDA"].last == 101.25
    assert cached["NVDA"].volume == 20
    assert cached["NVDA"].as_of.tzinfo is UTC


def test_postgres_quote_upsert_is_atomic_and_keeps_the_newest_value() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.statement = None
            self.committed = False

        def get_bind(self):
            return type("Bind", (), {"dialect": postgresql.dialect()})()

        def execute(self, statement) -> None:
            self.statement = statement

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            raise AssertionError("The valid upsert should not roll back.")

    session = FakeSession()
    upsert_quote_cache(
        session,
        {
            "NVDA": MarketQuote(
                symbol="NVDA",
                last=101.25,
                change_abs=2.25,
                change_pct=2.2727272727,
                volume=20,
                as_of=FETCHED_AT,
            )
        },
    )

    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (symbol) DO UPDATE" in sql
    assert "WHERE excluded.as_of >= quotes_cache.as_of" in sql
    assert session.committed is True


def test_market_hours_drive_required_poll_intervals() -> None:
    # 10:00 ET on a Wednesday in daylight-saving time.
    market_hour = datetime(2026, 7, 29, 14, 0, tzinfo=UTC)
    after_hours = datetime(2026, 7, 29, 21, 0, tzinfo=UTC)
    weekend = datetime(2026, 8, 1, 14, 0, tzinfo=UTC)

    assert is_us_market_open(market_hour) is True
    assert quote_poll_interval(market_hour) == 15
    assert is_us_market_open(after_hours) is False
    assert quote_poll_interval(after_hours) == 60
    assert quote_poll_interval(weekend) == 60
