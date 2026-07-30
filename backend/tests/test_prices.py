from datetime import UTC, datetime, timedelta

from backend.app.config import Settings, get_settings
from backend.app.db import get_db
from backend.app.models import QuoteCache
from backend.app.routers.prices import router
from backend.app.services.alpaca import (
    INDEX_SYMBOLS,
    PRICE_SYMBOLS,
    WATCHLIST_SYMBOLS,
    MarketBar,
    MarketQuote,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class FakeAlpacaClient:
    async def fetch_snapshots(self, symbols: tuple[str, ...]) -> dict[str, MarketQuote]:
        assert symbols == PRICE_SYMBOLS
        fetched_at = datetime.now(UTC)
        return {
            symbol: MarketQuote(
                symbol=symbol,
                last=100.0 + index,
                change_abs=1.0,
                change_pct=1.0,
                volume=1_000 + index,
                as_of=fetched_at,
            )
            for index, symbol in enumerate(symbols)
        }

    async def fetch_bars(self, symbol: str, range_name: str) -> list[MarketBar]:
        assert symbol == "NVDA"
        assert range_name == "1M"
        start = datetime(2026, 6, 1, 14, 0, tzinfo=UTC)
        return [
            MarketBar(
                time=start + timedelta(hours=index),
                open=100.0 + index,
                high=102.0 + index,
                low=99.0 + index,
                close=101.0 + index,
                volume=10_000 + index,
            )
            for index in range(60)
        ]


def _test_app(*, configured: bool, fake_client: FakeAlpacaClient | None = None) -> FastAPI:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    QuoteCache.__table__.create(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = FastAPI()
    app.include_router(router)
    app.state.alpaca_client = fake_client

    def override_db():
        with session_factory() as session:
            yield session

    settings = Settings(
        _env_file=None,
        alpaca_api_key_id="test-key" if configured else "",
        alpaca_api_secret_key="test-secret" if configured else "",
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    return app


def test_prices_refreshes_empty_cache_persists_and_groups_contract() -> None:
    app = _test_app(configured=True, fake_client=FakeAlpacaClient())

    with TestClient(app) as client:
        first = client.get("/api/prices")
        second = client.get("/api/prices")

    assert first.status_code == 200
    payload = first.json()
    assert payload["feed"] == "iex"
    assert payload["status"] == "live"
    assert set(payload["quotes"]) == set(WATCHLIST_SYMBOLS)
    assert set(payload["indices"]) == set(INDEX_SYMBOLS)
    assert payload["missing_symbols"] == []
    assert payload["source_label"] == "indicative (IEX)"
    assert second.status_code == 200
    for quote in [*payload["quotes"].values(), *payload["indices"].values()]:
        assert set(quote) == {"last", "change_abs", "change_pct", "volume", "as_of"}
        assert isinstance(quote["last"], float)
        assert isinstance(quote["volume"], int)


def test_prices_returns_structured_503_when_unconfigured_and_empty() -> None:
    app = _test_app(configured=False)

    with TestClient(app) as client:
        response = client.get("/api/prices")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["feed"] == "iex"
    assert payload["quotes"] == {}
    assert payload["indices"] == {}
    assert payload["error"]["code"] == "MARKET_DATA_UNAVAILABLE"


def test_one_month_bars_returns_at_least_fifty_real_points() -> None:
    app = _test_app(configured=True, fake_client=FakeAlpacaClient())

    with TestClient(app) as client:
        response = client.get("/api/bars", params={"symbol": "nvda", "range": "1M"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert payload["range"] == "1M"
    assert payload["feed"] == "iex"
    assert len(payload["bars"]) == 60
    assert set(payload["bars"][0]) == {
        "time",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }
    assert all(bar["close"] is not None for bar in payload["bars"])


def test_bars_validates_symbol_and_range() -> None:
    app = _test_app(configured=True, fake_client=FakeAlpacaClient())

    with TestClient(app) as client:
        bad_symbol = client.get("/api/bars", params={"symbol": "$NVDA", "range": "1M"})
        bad_range = client.get("/api/bars", params={"symbol": "NVDA", "range": "2Y"})

    assert bad_symbol.status_code == 422
    assert bad_range.status_code == 422
