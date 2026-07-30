import asyncio
from unittest.mock import patch

from backend.app.config import Settings
from backend.app.main import lifespan
from fastapi import FastAPI


def test_vercel_lifespan_skips_migrations_and_background_poller() -> None:
    settings = Settings(
        _env_file=None,
        vercel=True,
        alpaca_api_key_id="test-key",
        alpaca_api_secret_key="test-secret",
    )

    async def run() -> None:
        app = FastAPI()
        with (
            patch("backend.app.main.get_settings", return_value=settings),
            patch("backend.app.main.run_migrations") as run_migrations,
            patch("backend.app.main.AlpacaClient") as alpaca_client,
            patch("backend.app.main.run_quote_poller") as quote_poller,
        ):
            async with lifespan(app):
                assert app.state.quote_refresh_lock is not None
                assert app.state.quote_poller_task is None

            run_migrations.assert_not_called()
            alpaca_client.assert_not_called()
            quote_poller.assert_not_called()

    asyncio.run(run())
